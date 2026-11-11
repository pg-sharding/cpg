#!/usr/bin/env python3
"""Recount D3 recorded text evidence offline into a new outside directory; no PostgreSQL or network."""
import argparse
import hashlib
import json
import pathlib
import subprocess
import time
import traceback

HERE = pathlib.Path(__file__).resolve().parent


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--packet', type=pathlib.Path, default=HERE)
    parser.add_argument('--output', type=pathlib.Path, required=True, help='New directory outside the recorded packet')
    parser.add_argument('--qualification-only', action='store_true', help='Build/gate/codegen text recount only; timing evidence is not required')
    args = parser.parse_args()
    packet, output = args.packet.resolve(), args.output.resolve()
    assert not output.exists() and not output.is_relative_to(packet)
    assert packet.is_dir()
    output.mkdir(parents=True)
    status = dict(status='RUNNING_LOCAL_RECORDED_REPLAY', started_ns=time.time_ns(), commands=[],
                  runtime_execution=False, compiler_or_database_execution=False)

    def run(label, command):
        record = dict(label=label, args=command, started_ns=time.time_ns())
        status['commands'].append(record)
        with (output / (label + '.stdout.txt')).open('x') as stdout, (output / (label + '.stderr.txt')).open('x') as stderr:
            completed = subprocess.run(command, stdout=stdout, stderr=stderr, timeout=180)
        record.update(returncode=completed.returncode, finished_ns=time.time_ns())
        assert completed.returncode == 0, (label, 'Failure retained in the new output; recorded files unchanged')

    try:
        run('static', ['python3', '-B', str(packet / 'fresh-replay-r1/replay.py'), '--inputs', str(packet), '--static-check'])
        run('qualification', ['python3', '-B', str(packet / 'audit-build-qualification-r3.py'),
                             '--evidence', str(packet / 'evidence-qualification-r1'), '--output', str(output / 'qualification.json')])
        run('codegen', ['python3', '-B', str(packet / 'audit-normal-asm-r1.py'),
                       '--evidence', str(packet / 'evidence-qualification-r1'), '--output', str(output / 'codegen.json')])
        if not args.qualification_only:
            timing = packet / 'evidence-full-r1/timing-r1'
            run('smoke', ['python3', '-B', str(packet / 'timing-prep-r1/review-smoke-r1.py'),
                          '--timing-root', str(timing), '--output', str(output / 'smoke.json')])
            for cohort in range(2):
                run(f'analysis{cohort}', ['python3', '-B', str(packet / 'timing-prep-r1/analyze.py'),
                                         str(timing / f'cohort{cohort}'), str(output / f'analysis{cohort}-r1')])
            run('timing-recount', ['python3', '-B', str(packet / 'timing-prep-r1/audit-independent-r1.py'),
                                  '--run-root', str(timing), '--analysis0', str(output / 'analysis0-r1'),
                                  '--analysis1', str(output / 'analysis1-r1'),
                                  '--answers', str(packet / 'qualification/inputs/answers.json'),
                                  '--out-new', str(output / 'INDEPENDENT-FULL-RECOUNT-r1.json')])
        status.update(status='PASS_LOCAL_RECORDED_QUALIFICATION_REPLAY' if args.qualification_only else 'PASS_LOCAL_RECORDED_FULL_REPLAY',
                      finished_ns=time.time_ns(),
                      output_receipts={path.name: sha(path) for path in sorted(output.glob('*.json'))})
    except BaseException as exc:
        status.update(status='FAILED_LOCAL_REPLAY_PRESERVED', error=repr(exc), traceback=traceback.format_exc())
        raise
    finally:
        (output / 'status.json').write_text(json.dumps(status, indent=2) + '\n')
    print(json.dumps(status))


if __name__ == '__main__':
    main()
