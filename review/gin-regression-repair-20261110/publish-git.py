#!/usr/bin/env python3
"""Create an isolated results commit from a verified frozen packet, no checkout."""
import argparse
import hashlib
import json
import os
import pathlib
import subprocess

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--repo', type=pathlib.Path, required=True)
p.add_argument('--packet', type=pathlib.Path, required=True)
p.add_argument('--branch', required=True)
p.add_argument('--parent', default='8a8c475037bfde101da23cc9b0364c9c020eca93')
p.add_argument('--receipt', type=pathlib.Path, required=True)
a = p.parse_args()
packet = a.packet.resolve()
root = pathlib.Path(__file__).resolve().parent
index = root / 'publication-index'
assert not index.exists() and not a.receipt.exists()
assert a.branch == 'experiments/gin-regression-repair-results-b72-20261110'
prefix = 'review/gin-regression-repair-20261110/'
env = os.environ.copy()
env.update(GIT_INDEX_FILE=str(index), GIT_AUTHOR_NAME='root', GIT_AUTHOR_EMAIL='localhost',
           GIT_COMMITTER_NAME='root', GIT_COMMITTER_EMAIL='localhost',
           GIT_CONFIG_NOSYSTEM='1', GIT_CONFIG_GLOBAL='/dev/null', GIT_OPTIONAL_LOCKS='0')


def git(*args, data=None):
    return subprocess.check_output(['git', '-C', str(a.repo.resolve()), *args], input=data, env=env)


manifest = json.loads((packet / 'MANIFEST.json').read_text())
files = sorted(p for p in packet.rglob('*') if p.is_file())
assert {p.relative_to(packet).as_posix() for p in files} == set(manifest) | {'MANIFEST.json'}
for path in files:
    assert not path.is_symlink() and '__pycache__' not in path.parts
    name = path.relative_to(packet).as_posix()
    if name in manifest:
        value = manifest[name]
        assert path.stat().st_size == value['bytes'] and hashlib.sha256(path.read_bytes()).hexdigest() == value['sha256']
assert not git('ls-tree', '-r', '--name-only', a.parent, '--', prefix).strip()
assert subprocess.run(['git', '-C', str(a.repo), 'show-ref', '--verify', '--quiet', 'refs/heads/' + a.branch], env=env).returncode == 1
git('read-tree', a.parent)
updates = []
for path in files:
    name = prefix + path.relative_to(packet).as_posix()
    assert '\n' not in name and '\t' not in name
    blob = git('hash-object', '-w', '--stdin', data=path.read_bytes()).decode().strip()
    updates.append('100644 ' + blob + '\t' + name + '\n')
git('update-index', '--index-info', data=''.join(updates).encode())
tree = git('write-tree').decode().strip()
changed = git('diff', '--name-only', a.parent, tree).decode().splitlines()
assert len(changed) == len(files) and all(x.startswith(prefix) for x in changed)
assert not any(x.endswith(('regression.diffs', 'regression.out', 'postmaster.pid')) for x in changed)
message = ('Record GIN regression repair experiments\n\n'
           'Preserve layout and lazy/adaptive scan repair inputs, ordinary SQL\n'
           'qualification, both full benchmark cohorts, negative controls and\n'
           'reproduction commands. Include an unsent English RFC draft.\n')
commit = git('commit-tree', tree, '-p', a.parent, data=message.encode()).decode().strip()
git('update-ref', 'refs/heads/' + a.branch, commit, '0' * 40)
assert git('rev-parse', a.branch).decode().strip() == commit
result = dict(status='LOCAL_RESULTS_COMMIT_CREATED', commit=commit, tree=tree, parent=a.parent,
              branch=a.branch, files=len(files), bytes=sum(p.stat().st_size for p in files),
              manifest_sha256=hashlib.sha256((packet / 'MANIFEST.json').read_bytes()).hexdigest(),
              url='https://github.com/pg-sharding/cpg/tree/' + a.branch + '/' + prefix.rstrip('/'),
              worktree_untouched=True, main_branches_untouched=True)
a.receipt.write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps(result))
