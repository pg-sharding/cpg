#!/usr/bin/env python3
"""Finite serial coverage jobs; no source tuning, retries, or foreign jobs."""
import argparse
import json
import os
import pathlib
import shutil
import time
import traceback
from operations import bc, host

HERE = pathlib.Path(__file__).resolve().parent


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--namespace', required=True, type=pathlib.Path)
    parser.add_argument('--build', required=True, type=pathlib.Path)
    parser.add_argument('--qualified-from', required=True, type=pathlib.Path)
    args = parser.parse_args()
    bc.nice10()
    root = args.namespace.resolve()
    assert root.is_dir() and not (root / 'pipeline-status.json').exists()
    assert shutil.disk_usage(root).free > 30 * 1024 ** 3
    build = bc.checked_build(args.build)
    qualification = json.loads((args.qualified_from / 'status.json').read_text())
    assert qualification['status'] == 'PASS' and qualification['mode'] == 'qualify'
    assert not qualification['cleanup_errors'] and all(c['stopped'] for c in qualification['clusters'])
    frozen = json.loads((HERE / 'INPUTS.json').read_text())
    for name, expected in frozen['files'].items():
        p = HERE / name
        assert p.stat().st_size == expected['bytes'] and bc.sha(p) == expected['sha256']
    common = ['--build', args.build, '--qualified-from', args.qualified_from]
    jobs = [(name, ['python3', '-B', HERE / 'operations.py', '--operation', operation, *common,
                   '--output', root / name, '--first-port', '45700'])
            for name, operation in [('ci1', 'create-index'), ('in1', 'insert'), ('va1', 'vacuum')]]
    jobs += [('lg1', ['python3', '-B', HERE / 'scale.py', '--mode', 'warm', *common,
                     '--output', root / 'lg1', '--first-port', '45740']),
             ('rs1', ['python3', '-B', HERE / 'scale.py', '--mode', 'restart', *common,
                      '--large-from', root / 'lg1', '--output', root / 'rs1', '--first-port', '45740'])]
    state = dict(status='RUNNING', pid=os.getpid(), started_ns=time.time_ns(), host_before=host(),
                 jobs=[], build_receipt_sha256=bc.sha(args.build / 'build-receipt.json'),
                 input_manifest_sha256=bc.sha(HERE / 'INPUTS.json'))
    bc.save(root / 'pipeline-status.json', state)
    try:
        for name, command in jobs:
            state['phase'] = name
            state['host_current'] = host()
            bc.save(root / 'pipeline-status.json', state)
            bc.run(command, root / (name + '-runner.log'), timeout=3600)
            result = json.loads((root / name / 'status.json').read_text())
            assert result['status'] == 'PASS' and not result['cleanup_errors']
            assert all(c['stopped'] for c in result['clusters'])
            state['jobs'].append(dict(name=name, status='PASS', raw=result['raw'], retained=result['retained'],
                                      warm=result['warm'], stopped_clusters=len(result['clusters']),
                                      status_sha256=bc.sha(root / name / 'status.json')))
            bc.save(root / 'pipeline-status.json', state)
        bc.checked_build(args.build)
        state.update(status='PASS_FINITE_COVERAGE', finished_ns=time.time_ns(), host_after=host(),
                     raw=sum(j['raw'] for j in state['jobs']),
                     retained=sum(j['retained'] for j in state['jobs']),
                     warm=sum(j['warm'] for j in state['jobs']))
    except BaseException as exc:
        state.update(status='FAILED_PRESERVED_NO_RETRY', error=repr(exc), traceback=traceback.format_exc(),
                     finished_ns=time.time_ns())
        raise
    finally:
        bc.save(root / 'pipeline-status.json', state)


if __name__ == '__main__':
    main()
