#!/usr/bin/env python3
"""Create the canonical baseline layout control through an external Git index."""
import hashlib
import json
import os
import pathlib
import subprocess

HERE = pathlib.Path(__file__).resolve().parent
WORKSPACE = HERE.parents[2]
REPO = WORKSPACE / 'review/am-experiments-20261108/gin-fixed-performance-20261109/repository'
PARENT = '8a8c475037bfde101da23cc9b0364c9c020eca93'
BRANCH = 'experiments/gin-next-k4-layout-control-b72-20261111'
FILE = 'src/include/access/gin_private.h'
INDEX = HERE / 'C-external-index-r1'
assert not INDEX.exists()
environment = os.environ.copy()
environment.update(GIT_INDEX_FILE=str(INDEX), GIT_OPTIONAL_LOCKS='0',
                   GIT_AUTHOR_NAME='root', GIT_AUTHOR_EMAIL='localhost',
                   GIT_COMMITTER_NAME='root', GIT_COMMITTER_EMAIL='localhost')


def git(*args, data=None, indexed=True):
    e = environment.copy()
    if not indexed:
        e.pop('GIT_INDEX_FILE')
    return subprocess.check_output(['git', '-C', str(REPO), *args], input=data, env=e)


def state():
    return [git('rev-parse', 'HEAD', indexed=False),
            git('status', '--porcelain=v1', '-uno', indexed=False)]


before = state()
assert subprocess.run(['git', '-C', str(REPO), 'show-ref', '--verify', '--quiet',
                       'refs/heads/' + BRANCH]).returncode == 1
original = git('show', PARENT + ':' + FILE)
old = b'\tint\t\t\tnrequired;\n\tGinScanEntry *additionalEntries;\n\tint\t\t\tnadditional;'
new = b'\tint\t\t\tnrequired;\n\tint\t\t\tnadditional;\n\tGinScanEntry *additionalEntries;'
assert original.count(old) == 1 and b'GinTriConsistentCacheData' not in original
modified = original.replace(old, new)
assert modified != original
git('read-tree', PARENT)
blob = git('hash-object', '-w', '--stdin', data=modified).decode().strip()
git('update-index', '--add', '--cacheinfo', '100644,' + blob + ',' + FILE)
tree = git('write-tree').decode().strip()
message = b'''Keep the GIN scan-key entry counts adjacent

Move nadditional beside nrequired so the two counts occupy the existing
alignment region before additionalEntries. This layout-only control
leaves callback arguments and scan policies unchanged.
'''
commit = git('commit-tree', tree, '-p', PARENT, data=message).decode().strip()
assert git('diff-tree', '--no-commit-id', '--name-only', '-r', commit).decode().splitlines() == [FILE]
assert git('show', commit + ':' + FILE) == modified
git('update-ref', 'refs/heads/' + BRANCH, commit, '0' * 40)
assert state() == before
out = HERE / 'build-source/C'
(out / FILE).parent.mkdir(parents=True, exist_ok=True)
(out / FILE).write_bytes(modified)
(out / 'C-over-fixedB.diff').write_bytes(git('diff', PARENT, commit, '--'))
(out / 'C-over-fixedB.patch').write_bytes(git('format-patch', '-1', '--stdout', commit))
receipt = dict(status='CANONICAL_C_SOURCE_LOCAL_NOT_PUSHED', commit=commit, parent=PARENT,
               branch=BRANCH, author='root <localhost>', committer='root <localhost>',
               changed_file=FILE, parent_header_sha256=hashlib.sha256(original).hexdigest(),
               modified_header_sha256=hashlib.sha256(modified).hexdigest(),
               parent_worktree_and_HEAD_unchanged=True, backend_builds=0, timing_samples=0)
(HERE / 'SOURCE-COMMIT-C-r1.json').write_text(json.dumps(receipt, indent=2) + '\n')
INDEX.unlink()
print(json.dumps(receipt, indent=2))
