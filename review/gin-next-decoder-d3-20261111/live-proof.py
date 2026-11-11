#!/usr/bin/env python3
"""Root-executed read-only bindings and known-owned shutdown proof for D3; never signals or inspects foreign processes."""
import argparse
import hashlib
import importlib.util
import json
import os
import pathlib
import resource
import subprocess
import time
import traceback

PINS = {
    'BUILD-INPUTS-D3-r1.json': '34e3453794ebb4de2833865fc911d01350f16309aab1b2dee551be00d7a11267',
    'QUALIFICATION-INPUTS-D3-r1.json': '985ef80429245f6376e57a878d420eaf31be762a957c01b5ed37f603304f8b2d',
    'TIMING-INPUTS-D3-r1.json': '4fbf85da73d76807cdf1043ad1eb29d5b7576f40c4ac2c0088beabc28b07c5af',
}


def load(path):
    return json.loads(path.read_text())


def sha(path):
    return hashlib.sha256(pathlib.Path(path).read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=pathlib.Path, required=True)
    parser.add_argument('--stage', choices=['qualification', 'smoke', 'full'], required=True)
    parser.add_argument('--controller-pid', type=int, action='append', default=[], help='Known completed own controller PID; absence only, no /proc/exe reads')
    parser.add_argument('--output', type=pathlib.Path, required=True)
    args = parser.parse_args()
    root = args.root.resolve()
    assert root.name == 'gin-dec-d3-20261111' and not args.output.exists()
    assert args.output.resolve().is_relative_to(root)
    resource.setrlimit(resource.RLIMIT_AS, (3000000000, 3000000000))
    current = os.getpriority(os.PRIO_PROCESS, 0)
    if current < 10:
        os.nice(10 - current)
    state = dict(status='RUNNING_READONLY_D3_LIVE_PROOF', stage=args.stage, started_ns=time.time_ns(), timing_samples=0)
    try:
        inputs = root / 'inputs-full'
        required = ['BUILD-INPUTS-D3-r1.json', 'QUALIFICATION-INPUTS-D3-r1.json']
        if args.stage != 'qualification':
            required.append('TIMING-INPUTS-D3-r1.json')
        for name in required:
            assert sha(inputs / name) == PINS[name]
            for relative, binding in load(inputs / name)['files'].items():
                path = inputs / relative
                assert not path.is_symlink() and path.stat().st_size == binding['bytes'] and sha(path) == binding['sha256']
        loader = importlib.util.spec_from_file_location('bound_common', inputs / 'build-harness/common.py')
        bc = importlib.util.module_from_spec(loader)
        loader.loader.exec_module(bc)
        build = bc.checked_build(root / 'build-r1')
        assert build['source_plan_sha256'] == '59e277145711e1a3ad4ed3e942f9120c94203417071b0c3d27eda75634209007'
        source = load(root / 'build-r1/D3_assert-source-inventory.json')
        assert len(source) == 7726 and bc.inventory(build['common_source']) == source
        for role in ['B', 'D2', 'D3', 'D3_assert']:
            assert len(build['variants'][role]['headers']) == 907
            if role == 'D3_assert':
                continue  # Assertion configuration is not a release object comparison.
            for binding in build['variants'][role]['normal_objects'].values():
                assert sha(pathlib.Path(binding['asm'])) == binding['asm_sha256']
        q = load(root / 'qualification-r1/status.json')
        assert q['status'] == 'PASS_D3_ORDINARY_SQL_AND_VALID_DECODER'
        assert q['decoder_cases_per_variant'] == 21 and q['mixed_boundary_cases_per_variant'] == 192
        assert q['mixed_boundary_item_checks_per_variant'] == 8352 and q['timing_samples'] == 0
        assert q['build_receipt_sha256'] == sha(root / 'build-r1/build-receipt.json')
        qseed = load(root / 'qualification-r1/seed-inventory.json')
        assert bc.inventory(root / 'qualification-r1/seed') == qseed
        statuses = [q]
        unused = 0
        if args.stage != 'qualification':
            timing = root / 'timing-r1'
            freeze = load(timing / 'freeze.json')
            assert freeze['build_receipt_sha256'] == sha(root / 'build-r1/build-receipt.json')
            assert freeze['qualification_sha256'] == sha(root / 'qualification-r1/status.json')
            for name, binding in freeze['scripts'].items():
                assert (inputs / name).stat().st_size == binding['bytes'] and sha(inputs / name) == binding['sha256']
            seed = load(timing / 'seed-inventory.json')
            assert seed == qseed and bc.inventory(timing / 'seed') == seed
            for role, module in freeze['decoder_modules'].items():
                assert sha(module['path']) == module['sha256']
                assert module['headers_sha256'] == build['variants'][role]['headers_sha256']
            smoke = load(timing / 'smoke-status.json')
            assert smoke['status'] == 'PASS_SMOKE_NEEDS_ROOT_REVIEW' and smoke['timing_samples'] == 0
            assert smoke['unused_accepted_copies'] == 8
            native = load(timing / 'smoke/status.json')
            assert native['status'] == 'PASS' and native['raw'] == 112 and native['accepted_timing_samples'] == native['retained'] == 0
            runtime = load(timing / 'runtime-smoke.json')['roles']
            for key in ['prefix', 'backend_sha256', 'decoder_module', 'decoder_module_sha256']:
                assert runtime['B'][key] == runtime['T'][key]
            statuses.append(smoke)
            if args.stage == 'smoke':
                assert len(freeze['copies']) == 12
                for copy in freeze['copies'][4:]:
                    assert bc.inventory(copy['path']) == seed
                unused = 8
            else:
                run = load(timing / 'run-status.json')
                assert run['status'] == 'PASS_FIXED_SCREEN'
                assert (run['raw'], run['retained'], run['warm'], run['timing_samples']) == (3136, 2688, 448, 3136)
                statuses.append(run)
                assert args.controller_pid, 'Pass the actual completed accepted-run controller PID'
                for cohort in range(2):
                    directory = timing / f'cohort{cohort}'
                    value = load(directory / 'status.json')
                    assert value['status'] == 'PASS' and (value['raw'], value['retained']) == (1568, 1344)
                    assert value['raw_sha256'] == sha(directory / 'raw.jsonl')
                    assert value['literal_sha256'] == sha(directory / 'literal.jsonl')
            state['freeze_sha256'] = sha(timing / 'freeze.json')
            state['frozen_script_count'] = len(freeze['scripts'])
        stopped = []
        for status in statuses:
            assert status['cleanup_errors'] == [] and status['remaining_owned'] == 0
            for item in status['clusters']:
                assert item['stopped']
                proof = bc.stopped(item['prefix'], item['data'])
                assert not pathlib.Path(item['socket'], '.s.PGSQL.' + str(item['port'])).exists()
                for key in ['pid', 'backend_pid']:
                    assert not item.get(key) or not pathlib.Path('/proc', str(item[key])).exists()
                stopped.append(dict(label=item['label'], port=item['port'], proof=proof))
        assert len(stopped) == {'qualification': 5, 'smoke': 9, 'full': 17}[args.stage]
        for pid in args.controller_pid:
            assert pid > 1 and not pathlib.Path('/proc', str(pid)).exists()
        state.update(status='PASS_READONLY_D3_BINDINGS_AND_KNOWN_OWNED_STOPS', source_files=7726,
                     prefixes=4, headers_per_prefix=907, stopped_lifetimes=stopped, unused_copies_verified=unused,
                     controller_pids_gone=args.controller_pid, source_prefix_module_seed_inputs_unchanged=True,
                     build_receipt_sha256=sha(root / 'build-r1/build-receipt.json'),
                     qualification_sha256=sha(root / 'qualification-r1/status.json'),
                     load=list(os.getloadavg()), affinity=sorted(os.sched_getaffinity(0)),
                     cpu_topology=subprocess.check_output(['lscpu', '-e=CPU,CORE,SOCKET,ONLINE'], text=True, timeout=15),
                     process_scope='Known recorded owned PIDs only; no foreign /proc/exe inspection or signals', finished_ns=time.time_ns())
    except BaseException as exc:
        state.update(status='FAILED_READONLY_PROOF_PRESERVED', error=repr(exc), traceback=traceback.format_exc())
        raise
    finally:
        args.output.write_text(json.dumps(state, indent=2) + '\n')
    print(json.dumps({k: v for k, v in state.items() if k != 'stopped_lifetimes'}))


if __name__ == '__main__':
    main()
