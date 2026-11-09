#!/usr/bin/env python3
"""Fresh common B72 synthetic seed and ten stopped, hashed, fsynced copies."""
import argparse
import json
import os
import pathlib
import shlex
import shutil
import subprocess
import sys
import time
import traceback
from common import (HERE, sha, save, nice10, run, env, inventory, sync, stopped,
                    checked_build, socket_directory, local_dsn)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--build', type=pathlib.Path, required=True)
    parser.add_argument('--output', type=pathlib.Path, required=True,
                        help='New nonexistent root; no old PGDATA or holdout inputs')
    parser.add_argument('--port', type=int, default=40539)
    args = parser.parse_args()
    args.build, args.output = args.build.resolve(), args.output.resolve()
    assert 1024 <= args.port <= 65535
    args.output.mkdir(mode=0o700)
    nice10()
    receipt = checked_build(args.build)
    base = pathlib.Path(receipt['variants']['B']['prefix'])
    support = pathlib.Path(receipt['support'])
    seed = args.output / 'seed'
    socket = socket_directory(args.output / 'socket', args.port)
    started = False
    state = dict(status='RUNNING', pid=os.getpid(), started_ns=time.time_ns(),
                 timing_samples=0, accepted_samples=0,
                 AM_qualification='NOT RUN BY FIXTURE SCRIPT',
                 original_measurements_reproduced=False)
    save(args.output / 'status.json', state)
    try:
        run([base / 'bin/initdb', '-D', seed, '--no-locale', '--encoding=UTF8'],
            args.output / 'init.log', prefix=base)
        with (seed / 'postgresql.conf').open('a') as stream:
            stream.write("\nlisten_addresses=''\nshared_buffers='512MB'\n"
                         "autovacuum=off\njit=off\nmax_parallel_workers_per_gather=0\n"
                         "checkpoint_timeout='1h'\nlog_checkpoints=off\n"
                         "timing_clock_source=system\n")
        started = True
        run([base / 'bin/pg_ctl', '-D', seed, '-o',
             '-p' + str(args.port) + ' -k' + shlex.quote(str(socket)),
             '-l', args.output / 'private-seed-server.log', '-w', 'start'],
            args.output / 'start.log', prefix=base)
        dsn, psql = local_dsn(socket, args.port), base / 'bin/psql'
        run([psql, '-XAtq', '-d', dsn, '-v', 'ON_ERROR_STOP=1',
             '-v', 'module=' + str(support), '-f', HERE / 'setup.sql'],
            args.output / 'setup.log', prefix=base)
        holdout = args.output / 'holdout'
        run([sys.executable, HERE / 'prepare-holdout.py', '--psql', psql,
             '--dsn', dsn, '--output-dir', holdout],
            args.output / 'holdout.log', prefix=base)
        discovery = json.loads((holdout / 'holdout-discovery.json').read_text())
        assert discovery['probe_count'] == 3000 and discovery['absent_join_matches'] == 0
        run([sys.executable, HERE / 'verify-fixture.py', '--psql', psql,
             '--dsn', 'seed=' + dsn, '--output', args.output / 'full-multisets.json'],
            args.output / 'verify.log', prefix=base)
        run([base / 'bin/pg_ctl', '-D', seed, '-m', 'fast', '-w', 'stop'],
            args.output / 'stop.log', prefix=base)
        started = False
        stop = stopped(base, seed)
        sync(seed)
        before = inventory(seed)
        regular_bytes = sum(value['bytes'] for value in before.values())
        required_free = regular_bytes * 10 + (1 << 30)
        assert shutil.disk_usage(args.output).free >= required_free, (
            'need ten full copies plus 1 GiB free', required_free)
        save(args.output / 'seed-inventory.json', before)
        copies = []
        # Deliberately no role assignment: all ten copies finish before root maps roles.
        for cohort in range(2):
            for slot in range(5):
                destination = args.output / ('cohort%d-slot%d' % (cohort, slot))
                assert not destination.exists()
                begin = time.time_ns()
                shutil.copytree(seed, destination)
                assert inventory(destination) == before
                sync(destination)
                stopped(base, destination)
                copies.append(dict(cohort=cohort, slot=slot, global_copy_rank=len(copies),
                                   path=str(destination), begin_ns=begin,
                                   hash_fsync_end_ns=time.time_ns(), full_regular_files=len(before),
                                   full_regular_bytes=regular_bytes, full_tree_equal=True))
        assert len(copies) == 10 and inventory(seed) == before
        assert checked_build(args.build) == receipt
        assert sha(support) == receipt['support_sha256']
        state.update(status='PASS_NEW_SEED_AND_TEN_COPIES', finished_ns=time.time_ns(),
                     build_receipt_path=str(args.build / 'build-receipt.json'),
                     build_receipt_sha256=sha(args.build / 'build-receipt.json'),
                     source_plan_sha256=receipt['source_plan_sha256'], seed=str(seed),
                     seed_stop=stop, seed_full_inventory=before,
                     seed_inventory_sha256=sha(args.output / 'seed-inventory.json'),
                     seed_regular_bytes=regular_bytes, copies=copies,
                     all_copy_fsync_done_ns=time.time_ns(), roles_assigned=False,
                     holdout_receipt=str(holdout / 'holdout-discovery.json'),
                     holdout_receipt_sha256=sha(holdout / 'holdout-discovery.json'),
                     holdout_probes_path=str(holdout / 'holdout-probes.json'),
                     holdout_probes_sha256=sha(holdout / 'holdout-probes.json'),
                     support=str(support), support_sha256=sha(support),
                     cases_sha256=sha(HERE / 'cases.json'),
                     answers_sha256=sha(HERE / 'confirmation-answers.json'),
                     full_multisets_path=str(args.output / 'full-multisets.json'),
                     full_multisets_sha256=sha(args.output / 'full-multisets.json'),
                     input_sha256={name: sha(HERE / name) for name in
                                   ('setup.sql', 'cases.json', 'confirmation-answers.json',
                                    'prepare-holdout.py', 'verify-fixture.py')},
                     scope='Independent fresh seed; all ten copies before role assignment. '
                           'No source/core/AM/lifecycle/timing PASS inferred from fixture PASS.')
        save(args.output / 'fixture-receipt.json', state)
    except BaseException as exc:
        state.update(status='FAILED_PRESERVED', error=repr(exc), traceback=traceback.format_exc())
        raise
    finally:
        errors = []
        if started:
            try:
                if (seed / 'postmaster.pid').exists():
                    result = subprocess.run(
                        [str(base / 'bin/pg_ctl'), '-D', str(seed), '-m', 'fast', '-w', 'stop'],
                        env=env(base), capture_output=True, timeout=120)
                    state['finally_stop_rc'] = result.returncode
                    assert result.returncode == 0
                state['finally_stop'] = stopped(base, seed)
                sync(seed)
            except BaseException as exc:
                errors.append(repr(exc))
        state['cleanup_errors'] = errors
        if errors and state['status'] == 'PASS_NEW_SEED_AND_TEN_COPIES':
            state['status'] = 'FAILED_CLEANUP'
        save(args.output / 'status.json', state)
        if errors and not sys.exc_info()[0]:
            raise RuntimeError(('own seed cleanup failed', errors))


if __name__ == '__main__':
    main()
