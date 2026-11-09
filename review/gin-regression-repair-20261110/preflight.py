#!/usr/bin/env python3
"""Compile the L7 production units and verify actual scan-entry layouts."""
import argparse
import importlib.util
import json
import pathlib
import shlex
import shutil
import subprocess
import traceback

root = pathlib.Path(__file__).resolve().parent
loader = importlib.util.spec_from_file_location('bc', root / 'build-harness/common.py')
bc = importlib.util.module_from_spec(loader)
loader.loader.exec_module(bc)
p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--reference-build', type=pathlib.Path, required=True)
a = p.parse_args()
out = root / 'preflight-r1'
out.mkdir()
state = dict(status='RUNNING')
bc.save(out / 'status.json', state)
try:
    spec, baseline = bc.source_plan(root / 'build-source/SOURCE.json')
    prior = json.loads((a.reference_build / 'build-receipt.json').read_text())
    assert prior['base'] == spec['base']
    overlay = out / 'overlay/access'
    overlay.mkdir(parents=True)
    shutil.copy2(root / 'build-source/L7/src/include/access/gin_private.h', overlay / 'gin_private.h')
    prefix = pathlib.Path(prior['variants']['L4']['prefix'])
    pg = prefix / 'bin/pg_config'
    flags = shlex.split(bc.capture([pg, '--cflags'], prefix)) + shlex.split(bc.capture([pg, '--cppflags'], prefix))
    headers = pathlib.Path(bc.capture([pg, '--includedir-server'], prefix).strip())
    assert bc.inventory(headers) == prior['variants']['L4']['headers']
    for name in ['ginget', 'ginscan']:
        source = root / 'build-source/L7/src/backend/access/gin' / (name + '.c')
        bc.run(['gcc', *flags, '-Werror', '-fPIC', '-I' + str(overlay.parent),
                '-I' + str(headers), '-I' + str(prefix / 'include'), '-c', source,
                '-o', out / (name + '.o')], out / (name + '-compile.log'), prefix=prefix)
        bc.run(['objdump', '-drwC', out / (name + '.o')], out / (name + '-ASM.txt'))
    fields = ['queryKey', 'queryCategory', 'isPartialMatch', 'extra_data', 'strategy',
              'searchMode', 'attnum', 'buffer', 'curItem', 'matchBitmap', 'matchIterator',
              'matchResult', 'matchOffsets', 'matchNtuples', 'list', 'nlist', 'offset',
              'isFinished', 'reduceResult', 'predictNumberResult', 'btree']
    source = out / 'layout.c'
    text = '#include "postgres.h"\n#include "access/gin_private.h"\n#undef printf\nint main(void)\n{\n'
    text += 'printf("{\\\"bytes\\\":%zu", sizeof(GinScanEntryData));\n'
    for name in fields:
        text += 'printf(",\\\"' + name + '\\\":%zu", offsetof(GinScanEntryData, ' + name + '));\n'
    text += 'puts("}");\nreturn 0;\n}\n'
    source.write_text(text)
    layouts = {}
    for role in ['B', 'L4', 'L7']:
        prefix = pathlib.Path(prior['variants']['B' if role == 'B' else 'L4']['prefix'])
        inc = pathlib.Path(bc.capture([prefix / 'bin/pg_config', '--includedir-server'], prefix).strip())
        extra = ['-I' + str(overlay.parent)] if role == 'L7' else []
        bc.run(['gcc', *flags, *extra, '-I' + str(inc), '-I' + str(prefix / 'include'),
                source, '-o', out / ('layout-' + role)], out / ('layout-' + role + '-compile.log'), prefix=prefix)
        layouts[role] = json.loads(bc.capture([out / ('layout-' + role)], prefix))
    assert [layouts[r]['bytes'] for r in ['B', 'L4', 'L7']] == [824, 848, 832]
    assert all(layouts['B'][f] == layouts['L4'][f] == layouts['L7'][f] for f in fields)
    state.update(status='PASS', production_units=['ginget', 'ginscan'],
                 layouts=layouts, all_21_original_offsets_preserved=True,
                 compiler=bc.capture(['gcc', '--version']).splitlines()[0],
                 source_plan_sha256=bc.sha(root / 'build-source/SOURCE.json'),
                 source_units={n: bc.sha(root / 'build-source/L7/src/backend/access/gin' / (n + '.c'))
                               for n in ['ginget', 'ginscan']},
                 timing_or_full_backend_test=False)
except BaseException as exc:
    state.update(status='FAILED_PRESERVED', error=repr(exc), traceback=traceback.format_exc())
    raise
finally:
    bc.save(out / 'status.json', state)
print(json.dumps(state))
