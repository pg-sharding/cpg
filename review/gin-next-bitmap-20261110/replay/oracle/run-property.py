#!/usr/bin/env python3
"""Compile and execute the finite valid-offset fragment oracle, without timings."""
import argparse
import importlib.util
import json
import pathlib
import shlex
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from prepare import fragments

loader = importlib.util.spec_from_file_location('bitmap_build_common', HERE.parent / 'build-harness/common.py')
bc = importlib.util.module_from_spec(loader)
loader.loader.exec_module(bc)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--build', type=pathlib.Path, required=True)
    parser.add_argument('--output-new', type=pathlib.Path, required=True)
    a = parser.parse_args()
    a.output_new.mkdir()
    bc.nice10()
    build = bc.checked_build(a.build)
    prefix = pathlib.Path(build['variants']['B']['prefix'])
    original = bc.inventory(prefix, allow_symlinks=True)
    source = HERE.parent / 'source/src/backend/access/gin/ginget.c'
    data = fragments(source.read_bytes())
    data['offset-property.c'] = (HERE / 'offset-property.c').read_bytes()
    for name, value in data.items():
        (a.output_new / name).write_bytes(value)
    pg = prefix / 'bin/pg_config'
    flags = shlex.split(bc.capture([pg, '--cflags'], prefix)) + shlex.split(bc.capture([pg, '--cppflags'], prefix))
    headers = pathlib.Path(bc.capture([pg, '--includedir-server'], prefix).strip())
    state = dict(status='RUNNING', source_sha256=bc.sha(source),
                 build_receipt_sha256=bc.sha(a.build / 'build-receipt.json'),
                 files={n: dict(bytes=len(v), sha256=bc.sha(a.output_new / n)) for n, v in data.items()},
                 accepted_timing_samples=0, results={})
    bc.save(a.output_new / 'status.json', state)
    try:
        for mode, extra in [('normal', []), ('ubsan', ['-fsanitize=undefined', '-fno-sanitize-recover=all'])]:
            exe = a.output_new / ('offset-property-' + mode)
            bc.run(['gcc', *flags, '-Werror', *extra, '-I' + str(headers),
                    '-I' + str(prefix / 'include'), a.output_new / 'offset-property.c', '-o', exe],
                   a.output_new / (mode + '-compile.log'), prefix=prefix)
            log = a.output_new / (mode + '-run.json')
            bc.run([exe], log, prefix=prefix, timeout=180)
            result = json.loads(log.read_text())
            assert result['status'] == 'PASS_VALID_OFFSET_FRAGMENTS'
            assert result['max_ntuples'] >= 3 and result['max_offset'] > result['max_ntuples']
            assert all(result['skip_0_1_2_4_other_large'])
            state['results'][mode] = result
            bc.save(a.output_new / 'status.json', state)
        assert state['results']['normal'] == state['results']['ubsan']
        assert bc.inventory(prefix, allow_symlinks=True) == original
        bc.checked_build(a.build)
        state.update(status='PASS_VALID_OFFSET_FRAGMENTS_NORMAL_UBSAN', installed_tree_unchanged=True)
    except BaseException as exc:
        state.update(status='FAILED_PRESERVED', error=repr(exc))
        raise
    finally:
        bc.save(a.output_new / 'status.json', state)
    print(json.dumps(state))


if __name__ == '__main__':
    main()
