#!/usr/bin/env python3
"""Build the bounded offset-fragment executable; do not run timing workloads."""
import argparse
import hashlib
import importlib.util
import json
import pathlib
import shlex
import shutil
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import build_common as bc

loader = importlib.util.spec_from_file_location('extract_fragments', HERE / 'prepare-fragments.py')
extractor = importlib.util.module_from_spec(loader)
loader.loader.exec_module(extractor)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--build', type=pathlib.Path, required=True)
    p.add_argument('--qualified-from', type=pathlib.Path, required=True)
    p.add_argument('--output-new', type=pathlib.Path, required=True)
    a = p.parse_args()
    a.output_new.mkdir()
    bc.nice10()
    pins = json.loads((HERE / 'EXTERNAL-BINDINGS.json').read_text())
    assert bc.sha(a.build / 'build-receipt.json') == pins['build_receipt_sha256']
    assert bc.sha(a.qualified_from / 'status.json') == pins['qualification_status_sha256']
    gate = json.loads((a.qualified_from / 'status.json').read_text())
    assert gate['status'] == 'PASS' and gate['retained'] == 0 and not gate['cleanup_errors']
    build = bc.checked_build(a.build)
    assert build['source_plan_sha256'] == pins['source_plan_sha256']
    prefix = pathlib.Path(build['variants']['B']['prefix'])
    candidate = pathlib.Path(build['variants']['Bitmap']['prefix'])
    headers = prefix / 'include/server'
    header_inventory = bc.inventory(headers)
    assert len(header_inventory) == 907
    assert header_inventory == bc.inventory(candidate / 'include/server')
    fragments = extractor.extract((HERE / 'inputs/ginget-B.c').read_bytes(),
                                  (HERE / 'inputs/ginget-Bitmap.c').read_bytes())
    for name, value in fragments.items():
        (a.output_new / name).write_bytes(value)
    shutil.copyfile(HERE / 'offset-micro.c', a.output_new / 'offset-micro.c')
    state = dict(status='BUILDING_NO_TIMING', accepted_timing_samples=0,
                 build_receipt_sha256=bc.sha(a.build / 'build-receipt.json'),
                 qualification_status_sha256=bc.sha(a.qualified_from / 'status.json'),
                 headers=header_inventory, headers_identical_B_Bitmap=True,
                 fragments={n: dict(bytes=len(v), sha256=hashlib.sha256(v).hexdigest())
                            for n, v in fragments.items()})
    bc.save(a.output_new / 'status.json', state)
    try:
        pg = prefix / 'bin/pg_config'
        flags = shlex.split(bc.capture([pg, '--cflags'], prefix))
        flags += shlex.split(bc.capture([pg, '--cppflags'], prefix))
        executable = a.output_new / 'offset-micro'
        bc.run(['gcc', *flags, '-Werror', '-I' + str(headers),
                '-I' + str(prefix / 'include'), a.output_new / 'offset-micro.c',
                '-o', executable], a.output_new / 'normal-compile.log', prefix=prefix)
        bc.run(['objdump', '-drwCS', executable], a.output_new / 'normal-ASM.txt', prefix=prefix)
        bc.run(['nm', '-anS', executable], a.output_new / 'normal-nm.txt', prefix=prefix)
        asm = (a.output_new / 'normal-ASM.txt').read_text()
        assert '<offset_baseline>:' in asm and '<offset_candidate>:' in asm
        # The human codegen gate must independently inspect the main loop.
        # Merely seeing an indirect call does not establish that every iteration calls it.
        assert 'call' in asm and '*' in asm
        bc.checked_build(a.build)
        assert bc.inventory(headers) == header_inventory
        state.update(status='PASS_BUILD_REQUIRES_INDEPENDENT_ASM_REVIEW',
                     source_sha256=bc.sha(HERE / 'offset-micro.c'),
                     executable=str(executable.resolve()), executable_sha256=bc.sha(executable),
                     asm_sha256=bc.sha(a.output_new / 'normal-ASM.txt'),
                     nm_sha256=bc.sha(a.output_new / 'normal-nm.txt'), flags=flags,
                     installed_trees_unchanged=True)
    except BaseException as exc:
        state.update(status='FAILED_PRESERVED', error=repr(exc))
        raise
    finally:
        bc.save(a.output_new / 'status.json', state)
    print(json.dumps({k: v for k, v in state.items() if k != 'headers'}))


if __name__ == '__main__':
    main()
