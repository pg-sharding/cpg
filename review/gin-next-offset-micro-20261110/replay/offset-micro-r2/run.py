#!/usr/bin/env python3
"""Fixed offset-fragment micro only; no AM, SQL, compilation or automatic promotion."""
import argparse
import hashlib
import itertools
import json
import os
import pathlib
import resource
import subprocess
import time
import traceback

import build_common as bc

HERE = pathlib.Path(__file__).resolve().parent
ROLES = ['B', 'T', 'Bitmap']


def design(mode):
    cells = [dict(name=f'n{n}_skip{skip}', n=n, skip=skip, loops=250000)
             for n in [8, 64, 291] for skip in [0, 1, 2, 4, n - 1]]
    first = [[ROLES[(i + shift) % 3] for i in [0, 1, 2]] for shift in range(3)]
    orders = first + [list(reversed(x)) for x in first]
    assert set(map(tuple, orders)) == set(itertools.permutations(ROLES))
    warm, retained, cohorts = (1, 0, 1) if mode == 'smoke' else (2, 6, 2)
    return dict(mode=mode, cases=cells, roles=ROLES, orders=orders, warmups=warm,
                retained_rounds=retained, cohorts=cohorts,
                raw=15 * 3 * (warm + retained) * cohorts,
                retained=15 * 3 * retained * cohorts, warm=15 * 3 * warm * cohorts)


def host():
    return dict(uname=list(os.uname()), load=list(os.getloadavg()),
                affinity=sorted(os.sched_getaffinity(0)), realtime_ns=time.time_ns())


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--build', type=pathlib.Path, required=True)
    p.add_argument('--micro-build', type=pathlib.Path, required=True)
    p.add_argument('--codegen-review', type=pathlib.Path, required=True)
    p.add_argument('--output-new', type=pathlib.Path, required=True)
    p.add_argument('--mode', choices=['smoke', 'screen'], required=True)
    a = p.parse_args()
    a.output_new.mkdir()
    bc.nice10()
    initial_affinity = os.sched_getaffinity(0)
    assert {0, 4} <= initial_affinity
    spec = design(a.mode)
    micro = json.loads((a.micro_build / 'status.json').read_text())
    assert micro['status'] == 'PASS_BUILD_REQUIRES_INDEPENDENT_ASM_REVIEW'
    executable = pathlib.Path(micro['executable'])
    assert bc.sha(executable) == micro['executable_sha256']
    assert bc.sha(a.micro_build / 'normal-ASM.txt') == micro['asm_sha256']
    review = json.loads(a.codegen_review.read_text())
    assert review['status'] == 'PASS_INDEPENDENT_OFFSET_MICRO_CODEGEN_REVIEW'
    assert review['executable_sha256'] == micro['executable_sha256']
    assert review['asm_sha256'] == micro['asm_sha256']
    assert review['source_sha256'] == bc.sha(HERE / 'offset-micro.c') == micro['source_sha256']
    assert review['indirect_call_each_kernel_iteration'] is True
    build = bc.checked_build(a.build)
    assert bc.sha(a.build / 'build-receipt.json') == micro['build_receipt_sha256']
    final_source = json.loads((a.build / 'Bitmap_assert-source-inventory.json').read_text())
    assert bc.inventory(pathlib.Path(build['common_source'])) == final_source
    frozen = {p.relative_to(HERE).as_posix(): dict(bytes=p.stat().st_size, sha256=bc.sha(p))
              for p in sorted(HERE.rglob('*')) if p.is_file() and '__pycache__' not in p.parts}
    state = dict(status='RUNNING', mode=a.mode, raw=0, retained=0,
                 host_before=host(), build_receipt_sha256=bc.sha(a.build / 'build-receipt.json'),
                 micro_build_status_sha256=bc.sha(a.micro_build / 'status.json'),
                 codegen_review_sha256=bc.sha(a.codegen_review), executable_sha256=bc.sha(executable),
                 scope='Extracted exact offset fragments with actual PG types, not a full GIN AM. '
                       'Common indirect-call overhead remains. Kernel clocks exclude process startup/validation; '
                       'outer process elapsed/CPU include startup. No accepted SQL results arise here.')
    bc.save(a.output_new / 'status.json', state)
    bc.save(a.output_new / 'protocol.json', spec)
    bc.save(a.output_new / 'frozen-inputs.json', frozen)
    try:
        with (a.output_new / 'raw.jsonl').open('x') as raw:
            for cohort in range(spec['cohorts']):
                kernel_cpu, client_cpu = (0, 4) if cohort == 0 else (4, 0)
                os.sched_setaffinity(0, {client_cpu})
                state['host_cohort_' + str(cohort)] = host()
                bc.save(a.output_new / 'status.json', state)
                cases = list(reversed(spec['cases'])) if cohort else spec['cases']
                for cell in cases:
                    for round_ in range(spec['warmups'] + spec['retained_rounds']):
                        order = spec['orders'][round_ if round_ < spec['warmups'] else round_ - spec['warmups']]
                        for place, role in enumerate(order):
                            selector = int(role == 'Bitmap')
                            args = ['taskset', '-c', str(kernel_cpu), str(executable), str(selector),
                                    str(cell['n']), str(cell['skip']), str(cell['loops'])]
                            before = resource.getrusage(resource.RUSAGE_CHILDREN)
                            begin = time.monotonic_ns()
                            observed = subprocess.run(args, env=bc.env(), capture_output=True,
                                                      text=True, timeout=30, start_new_session=True)
                            elapsed = time.monotonic_ns() - begin
                            after = resource.getrusage(resource.RUSAGE_CHILDREN)
                            row = dict(cohort=cohort, case=cell['name'], role=role, selector=selector,
                                       kernel_cpu=kernel_cpu, client_cpu=client_cpu, round=round_,
                                       position=place, order=order, retained=round_ >= spec['warmups'],
                                       command=args, returncode=observed.returncode,
                                       stdout=observed.stdout, stderr=observed.stderr, outer_wall_ns=elapsed,
                                       outer_cpu_ns=round(((after.ru_utime + after.ru_stime) -
                                                          (before.ru_utime + before.ru_stime)) * 1e9))
                            raw.write(json.dumps(row) + '\n')
                            raw.flush()
                            os.fsync(raw.fileno())
                            assert observed.returncode == 0 and not observed.stderr
                            value = json.loads(observed.stdout)
                            assert value['status'] == 'PASS_OFFSET_FRAGMENT'
                            assert (value['n'], value['skip'], value['loops']) == (cell['n'], cell['skip'], cell['loops'])
                            assert value['checksum'] == cell['skip'] * cell['loops']
                            assert value['cpu_ns'] > 0 and value['wall_ns'] > 0
                            state['raw'] += 1
                            state['retained'] += int(row['retained'])
                    state['last_case'] = cell['name']
                    bc.save(a.output_new / 'status.json', state)
        assert (state['raw'], state['retained']) == (spec['raw'], spec['retained'])
        assert bc.sha(executable) == micro['executable_sha256']
        bc.checked_build(a.build)
        assert bc.inventory(pathlib.Path(build['common_source'])) == final_source
        for name, value in frozen.items():
            assert (HERE / name).stat().st_size == value['bytes'] and bc.sha(HERE / name) == value['sha256']
        state.update(status='PASS_FIXED_OFFSET_FRAGMENT_CAMPAIGN', raw_sha256=bc.sha(a.output_new / 'raw.jsonl'),
                     warm=spec['warm'], source_install_inputs_executable_unchanged=True,
                     host_after=host(), owned_cluster_lifetimes=0, finished_ns=time.time_ns())
    except BaseException as exc:
        state.update(status='FAILED_PRESERVED', error=repr(exc), traceback=traceback.format_exc())
        raise
    finally:
        os.sched_setaffinity(0, initial_affinity)
        bc.save(a.output_new / 'status.json', state)
    print(json.dumps(state))


if __name__ == '__main__':
    main()
