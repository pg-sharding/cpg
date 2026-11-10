#!/usr/bin/env python3
"""Local AST/help/exact-source checks only; does not compile or execute PostgreSQL."""
import argparse
import ast
import hashlib
import importlib.util
import json
import pathlib
import subprocess
import sys

HERE = pathlib.Path(__file__).resolve().parent

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--git', type=pathlib.Path, default=HERE / 'repository')
    p.add_argument('--startup-root', type=pathlib.Path, default=HERE.parent.parent / 'startup-decoder')
    p.add_argument('--output', type=pathlib.Path, required=True)
    a = p.parse_args()
    assert not a.output.exists()
    files = []
    for folder in ('full-build-harness-r1', 'full-qualification-r1'):
        for path in sorted((HERE / folder).rglob('*.py')):
            ast.parse(path.read_text(), filename=str(path)); files.append(str(path.relative_to(HERE)))
    helps = {}
    for name in ('full-build-harness-r1/build.py', 'full-qualification-r1/qualify.py'):
        q = subprocess.run([sys.executable, '-B', str(HERE / name), '--help'], capture_output=True, text=True, timeout=30)
        assert q.returncode == 0, q.stderr
        helps[name] = dict(returncode=q.returncode, stdout_sha256=hashlib.sha256(q.stdout.encode()).hexdigest())
    spec_loader = importlib.util.spec_from_file_location('bc', HERE / 'full-build-harness-r1/common.py')
    bc = importlib.util.module_from_spec(spec_loader); spec_loader.loader.exec_module(bc)
    spec, baseline = bc.source_plan(HERE / 'full-build-source-r1/SOURCE.json')
    def git(*args):
        return subprocess.check_output(['git', '-C', str(a.git), *args], env=bc.env())
    assert git('rev-parse', spec['base']).decode().strip() == spec['base']
    for role, variant in spec['variants'].items():
        commit = variant['commit']
        patch = HERE / 'full-build-source-r1' / variant['patch']['path']
        assert git('diff', '--binary', spec['base'], commit, '--') == patch.read_bytes()
        changes = set(git('diff', '--name-only', spec['base'], commit, '--').decode().splitlines())
        assert changes == set(variant['source_files'])
        for name in changes:
            assert git('show', commit + ':' + name) == (HERE / 'full-build-source-r1' / role / name).read_bytes()
    qroot = HERE / 'full-qualification-r1'
    copied = ['session.py'] + [str(p.relative_to(a.startup_root / 'qualification')) for p in sorted((a.startup_root / 'qualification/inputs').rglob('*')) if p.is_file()]
    for name in copied:
        assert (qroot / name).read_bytes() == (a.startup_root / 'qualification' / name).read_bytes(), name
    for name in ['vector-probe.c', 'probe-setup.sql']:
        assert (qroot / name).read_bytes() == (HERE / 'probe-r2' / name).read_bytes()
    module_loader = importlib.util.spec_from_file_location('newqual', qroot / 'qualify.py')
    sys.path.insert(0, str(qroot))
    module = importlib.util.module_from_spec(module_loader); module_loader.loader.exec_module(module)
    assert len(module.NATIVE_QUERIES) == 11 and len(module.FALLBACK_CASES) == 11 and len(module.extra_cases()) == 15
    assert sum(3 ** (n + int(hidden)) for _, _, n, hidden in module.NATIVE_QUERIES) == 45993
    result = dict(status='PASS_STATIC_ONLY_NOT_FULL_BUILD_OR_SQL', source_plan_sha256=sha(HERE / 'full-build-source-r1/SOURCE.json'),
                  ast=files, command_help=helps, source_roles=list(spec['variants']), source_files=7726,
                  copied_fixture_files=copied, native_vectors_per_variant=45993, native_checks_per_variant=183972,
                  full_build_executed=False, full_SQL_executed=False, timing_samples=0)
    a.output.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result))

if __name__ == '__main__':
    main()
