#!/usr/bin/env python3
"""Qualify actual production translation units before the r3 builds."""
import argparse
import importlib.util
import json
import pathlib
import shlex
import shutil
import traceback

root = pathlib.Path(__file__).resolve().parent
loader = importlib.util.spec_from_file_location('bc', root / 'build-harness/common.py')
bc = importlib.util.module_from_spec(loader)
loader.loader.exec_module(bc)
p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--reference-build', type=pathlib.Path, required=True)
a = p.parse_args()
out = root / 'preflight'
out.mkdir()
state = dict(status='RUNNING', production_units=[])
try:
    spec, baseline = bc.source_plan(root / 'build-source/SOURCE.json')
    prior = json.loads((a.reference_build / 'build-receipt.json').read_text())
    assert prior['base'] == spec['base']
    overlay = out / 'overlay/access'
    overlay.mkdir(parents=True)
    shutil.copy2(root / 'build-source/L4/src/include/access/gin_private.h', overlay / 'gin_private.h')
    for label, role, reference in [('L8', 'L8', 'L4'), ('L9', 'L9', 'L4'),
                                   ('C9', 'C9', 'L4'), ('C9_assert', 'C9', 'L7_assert')]:
        prefix = pathlib.Path(prior['variants'][reference]['prefix'])
        pg = prefix / 'bin/pg_config'
        flags = shlex.split(bc.capture([pg, '--cflags'], prefix)) + shlex.split(bc.capture([pg, '--cppflags'], prefix))
        headers = pathlib.Path(bc.capture([pg, '--includedir-server'], prefix).strip())
        assert bc.inventory(headers) == prior['variants'][reference]['headers']
        source = root / 'build-source' / role / 'src/backend/access/gin/ginget.c'
        obj = out / (label + '.o')
        bc.run(['gcc', *flags, '-Werror', '-fPIC', '-I' + str(overlay.parent),
                '-I' + str(headers), '-I' + str(prefix / 'include'), '-c', source, '-o', obj],
               out / (label + '-compile.log'), prefix=prefix)
        bc.run(['objdump', '-drwC', obj], out / (label + '-ASM.txt'))
        state['production_units'].append(dict(label=label, source_sha256=bc.sha(source),
                                             object_sha256=bc.sha(obj), reference=reference))
    state.update(status='PASS', source_plan_sha256=bc.sha(root / 'build-source/SOURCE.json'),
                 tests_or_timings=False)
except BaseException as exc:
    state.update(status='FAILED_PRESERVED', error=repr(exc), traceback=traceback.format_exc())
    raise
finally:
    bc.save(out / 'status.json', state)
print(json.dumps(state))
