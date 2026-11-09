#!/usr/bin/env python3
"""Data-only source composition/fixture checks; never compile or start a server."""
import argparse
import ast
import json
import os
import pathlib
import subprocess
import sys
import tempfile
from common import HERE, ROLES, sha, save, source_plan, env


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--git', type=pathlib.Path, required=True,
                        help='Existing local public-source object repository; read-only')
    parser.add_argument('--source-plan', type=pathlib.Path,
                        default=HERE.parent / 'source/SOURCE.json')
    parser.add_argument('--output', type=pathlib.Path, required=True)
    args = parser.parse_args()
    assert not args.output.exists()
    plan = args.source_plan.resolve()
    spec, baseline = source_plan(plan)
    changed = set().union(*(v['source_files'] for v in spec['variants'].values()))
    assert changed == {'src/backend/access/hash/hash.c', 'src/backend/access/hash/hashinsert.c',
                       'src/backend/access/hash/hashpage.c', 'src/backend/access/hash/hashsearch.c',
                       'src/include/access/hash.h'}
    snapshots = {}
    for role in ROLES:
        commit = spec['variants'][role]['commit']
        paths = subprocess.check_output(
            ['git', '-C', str(args.git), 'diff', '--name-only', spec['base'], commit],
            env=env(), text=True).splitlines()
        assert set(paths) == set(spec['variants'][role]['source_files'])
        snapshots[role] = {}
        for name in sorted(changed):
            data = subprocess.check_output(['git', '-C', str(args.git), 'show',
                                            commit + ':' + name], env=env())
            wanted = spec['variants'][role]['source_files'].get(name, baseline[name])
            import hashlib
            assert len(data) == wanted['bytes']
            assert hashlib.sha256(data).hexdigest() == wanted['sha256']
            snapshots[role][name] = data
    name = 'src/backend/access/hash/hashsearch.c'
    before = (b'if (so->hashso_sk_hash == _hash_get_indextuple_hashkey(itup) &&\n'
              b'\t\t\t\t_hash_checkqual(scan, itup))')
    after = b'if (so->hashso_sk_hash == _hash_get_indextuple_hashkey(itup))'
    assert snapshots['B'][name].count(before) == snapshots['H'][name].count(before) == 2
    assert snapshots['B'][name].replace(before, after) == snapshots['N'][name]
    assert snapshots['H'][name].replace(before, after) == snapshots['C'][name]
    for name in changed - {'src/backend/access/hash/hashsearch.c'}:
        assert snapshots['B'][name] == snapshots['N'][name]
        assert snapshots['H'][name] == snapshots['C'][name]
    replays = []
    for order in [('N', 'H'), ('H', 'N')]:
        with tempfile.TemporaryDirectory(prefix='hash-composition-data-') as temporary:
            root = pathlib.Path(temporary)
            for name, data in snapshots['B'].items():
                target = root / name
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(data)
            for role in order:
                patch = plan.parent / spec['variants'][role]['patch']['path']
                subprocess.run(['patch', '--batch', '--forward', '--fuzz=0', '-p1', '-i',
                                str(patch)], cwd=root, env=env(), capture_output=True, check=True)
            assert all((root / name).read_bytes() == data
                       for name, data in snapshots['C'].items())
            replays.append(dict(order=list(order), exact_C_snapshots=True))
    cases = json.loads((HERE / 'cases.json').read_text())['cases']
    original = json.loads((HERE / 'cases-original18.json').read_text())['cases']
    answers = json.loads((HERE / 'confirmation-answers.json').read_text())
    original_answers = json.loads((HERE / 'answers-original18.json').read_text())
    assert len(cases) == 19 and len(original) == 18 and cases[:18] == original
    assert {name: answers[name] for name in original_answers} == original_answers
    residual = cases[-1]
    assert residual['name'] == 'uniform_hot_varying_residual'
    assert residual['expected_index_loops'] == 3000
    assert residual['require_memoize_enabled'] is True
    # Uniform k=id; hot key 123456; p.id=1..3000; threshold 122000+p.id.
    matches = sum(123456 <= 122000 + identifier for identifier in range(1, 3001))
    assert matches == 1545 and matches * 123456 == 190739520
    assert answers[residual['name']]['answer'] == '3000|1545|190739520'
    syntax, helps = [], []
    for path in sorted(HERE.rglob('*.py')):
        ast.parse(path.read_text())
        syntax.append(dict(path=path.relative_to(HERE).as_posix(), sha256=sha(path)))
    for name in ('build.py', 'prepare-fixture.py', 'verify-fixture.py', 'prepare-holdout.py',
                 'gate.py', 'static-check.py'):
        output = subprocess.check_output([sys.executable, '-B', str(HERE / name), '--help'],
                                         env=dict(env(), PYTHONDONTWRITEBYTECODE='1'), text=True)
        assert 'usage:' in output
        helps.append(name)
    save(args.output, dict(status='PASS_STATIC_ONLY', source_plan_sha256=sha(plan),
                           commits={role: spec['variants'][role]['commit'] for role in ROLES},
                           exact_five_file_Git_snapshots=True,
                           all_Git_changed_paths_exact=True,
                           N_only_two_predicate_removals=True,
                           C_equals_H_plus_exact_N_removals=True,
                           strict_patch_replays=replays,
                           original18_objects_and_answers_unchanged=True,
                           case19_independent_formula=dict(matches=matches, sum=matches * 123456),
                           AST=syntax, help=helps, new_compiler_VM_SQL_seed_timing='NOT EXECUTED'))


if __name__ == '__main__':
    main()
