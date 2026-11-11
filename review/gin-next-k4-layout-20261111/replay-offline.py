#!/usr/bin/env python3
"""Regenerate separate K4 r1/r2 analyses, root/peer audits and tables to new output."""
import argparse
import hashlib
import json
import pathlib
import subprocess
import sys


def load(path):
    return json.loads(path.read_text())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--packet', type=pathlib.Path, required=True)
    parser.add_argument('--out-new', type=pathlib.Path, required=True)
    parser.add_argument('--attempt', choices=['both', 'r1', 'r2'], default='both')
    args = parser.parse_args()
    packet, out = args.packet.resolve(), args.out_new.resolve()
    assert not out.exists() and not out.is_relative_to(packet)
    for manifest in ['BUILD-INPUTS-K4-r1.json', 'RUNTIME-INPUTS-K4-r1.json']:
        for name, item in load(packet / manifest)['files'].items():
            path = packet / name
            assert path.stat().st_size == item['bytes'] and sha(path) == item['sha256']
    attempts = ['r1', 'r2'] if args.attempt == 'both' else [args.attempt]
    out.mkdir()
    commands = []
    def run(command):
        command = list(map(str, command))
        completed = subprocess.run(command, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        commands.append(dict(command=command, returncode=completed.returncode))
        assert completed.returncode == 0, completed.stderr[-8000:]
    for tag in attempts:
        target = out / tag
        target.mkdir()
        evidence = packet / ('evidence-' + tag)
        relative = 'timing-r1' if tag == 'r1' else 'r2/timing-r2'
        timing = evidence / relative
        for cohort in [0, 1]:
            name = 'analysis-cohort' + str(cohort) + '-' + tag
            run([sys.executable, '-B', packet / 'timing-prep-r1/analyze.py',
                 timing / ('cohort' + str(cohort)), target / name])
            for filename in ['absolute.json', 'pairs.json', 'status.json']:
                assert load(target / name / filename) == load(packet / name / filename), (name, filename)
        run([sys.executable, '-B', packet / 'audit-results-r2.py', '--evidence', evidence,
             '--timing-name', relative, '--analysis-root', target, '--full', '--output', target / 'ROOT-AUDIT-REPLAY.json'])
        command = [sys.executable, '-B', packet / 'peer-recount.py', '--packet', packet,
                   '--evidence', evidence, '--timing-name', relative, '--analysis-root', target,
                   '--output', target / 'PEER-AUDIT-REPLAY.json']
        if tag == 'r2':
            command += ['--reference-evidence', packet / 'evidence-r1']
        run(command)
        run([sys.executable, '-B', packet / 'render-tables.py', '--analysis-root', target,
             '--peer-receipt', target / 'PEER-AUDIT-REPLAY.json', '--out-new', target / 'tables', '--attempt', tag])
    receipt = dict(status='PASS_OFFLINE_REPLAY_NO_NEW_TIMINGS', attempts=attempts,
                   bundled_analysis_JSON_equal=True, commands=commands,
                   final_packet_manifest_required=False,
                   scope='Frozen input manifests, collections, complete analysis groups, root/independent peer recounts and all-metric rendering. No network/compiler/backend. Final environment/monitor interpretation is separate.')
    (out / 'REPLAY.json').write_text(json.dumps(receipt, indent=2) + '\n')
    print(json.dumps(receipt))


if __name__ == '__main__':
    main()
