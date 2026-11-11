#!/usr/bin/env python3
"""Offline restoration, independent ordinary-gate recount and full numerical replay; no PostgreSQL/compiler/network."""
import argparse
import hashlib
import json
import pathlib
import shutil
import subprocess
import sys

HERE = pathlib.Path(__file__).resolve().parent


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--packet', type=pathlib.Path, default=HERE)
    parser.add_argument('--output', type=pathlib.Path, required=True, help='New nonexistent local output directory')
    args = parser.parse_args()
    packet = args.packet.resolve()
    output = args.output.resolve()
    output.mkdir()
    commands = []

    def run(arguments):
        command = [sys.executable, '-B', *map(str, arguments)]
        result = subprocess.run(command, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        commands.append(dict(command=command, returncode=result.returncode, stdout=result.stdout, stderr=result.stderr))
        (output / 'commands.json').write_text(json.dumps(commands, indent=2) + '\n')
        assert result.returncode == 0, 'Offline failed attempt preserved'

    run([packet / 'fresh-replay-r1/replay.py', '--inputs', packet / 'inputs', '--static-check'])
    run([packet / 'restore-raw-r1.py', '--packet', packet, '--output', output / 'timing-r1'])
    # Bind the unchanged historical metadata auditor to a fresh local input view.
    view = output / 'ordinary-audit-input-view'
    view.mkdir()
    shutil.copytree(packet / 'inputs', view, dirs_exist_ok=True)
    for name in ['audit-build-qualification-r2.py', 'ROOT-COLLECTION-BUILD-QUALIFICATION-r1.json']:
        shutil.copyfile(packet / 'reviews' / name, view / name)
    run([view / 'audit-build-qualification-r2.py', '--evidence', packet / 'recorded/build-qualification-r1',
         '--output', output / 'ordinary-audit.json'])
    run([packet / 'inputs/timing-prep-r1/review-smoke-r1.py', '--timing-root', output / 'timing-r1',
         '--answers', packet / 'inputs/qualification/inputs/answers.json', '--output', output / 'smoke-audit.json'])
    for cohort in range(2):
        run([packet / 'inputs/timing-prep-r1/analyze.py', output / f'timing-r1/cohort{cohort}', output / f'analysis{cohort}'])
        for name in ['absolute.json', 'pairs.json', 'status.json']:
            assert sha(output / f'analysis{cohort}' / name) == sha(packet / f'analysis{cohort}-r1' / name)
    run([packet / 'inputs/timing-prep-r1/audit-independent-r1.py', '--run-root', output / 'timing-r1',
         '--analysis0', output / 'analysis0', '--analysis1', output / 'analysis1',
         '--answers', packet / 'inputs/qualification/inputs/answers.json', '--out-new', output / 'full-audit.json'])
    full = json.loads((output / 'full-audit.json').read_text())
    assert full == json.loads((packet / 'reviews/INDEPENDENT-FULL-RECOUNT-r1.json').read_text())
    ordinary = json.loads((output / 'ordinary-audit.json').read_text())
    expected = json.loads((packet / 'reviews/BUILD-QUALIFICATION-INDEPENDENT-AUDIT-r2.json').read_text())
    for name in ['started_ns', 'finished_ns']:
        ordinary.pop(name, None)
        expected.pop(name, None)
    assert ordinary == expected
    result = dict(status='PASS_OFFLINE_RECORDED_D2_REPLAY', restored_timing_files=len(json.loads((packet / 'recorded/timing-manifest.json').read_text())['files']),
                  raw=full['raw'], retained=full['retained'], warm=full['warm'], numeric_comparisons=full['numeric_comparisons'],
                  all_six_analysis_files_byte_identical=True, ordinary_recount_equal_except_timestamps=True,
                  new_Linux_build_or_runtime='NOT_EXECUTED', commands=len(commands))
    (output / 'status.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result))


if __name__ == '__main__':
    main()
