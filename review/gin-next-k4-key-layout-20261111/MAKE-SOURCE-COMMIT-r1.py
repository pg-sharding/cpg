#!/usr/bin/env python3
"""Record one layout experiment using an external index; keep HEAD unchanged."""
import hashlib
import json
import os
import pathlib
import subprocess

HERE = pathlib.Path(__file__).resolve().parent
WORKSPACE = HERE.parents[2]
REPOSITORY = WORKSPACE / 'review/am-experiments-20261108/gin-fixed-performance-20261109/repository'
PARENT = 'ec32d586cf3bb6cfa76eb672db70160b436ce47c'
BASE = '8a8c475037bfde101da23cc9b0364c9c020eca93'
BRANCH = 'experiments/gin-next-k4-key-layout-b72-20261111'
PATH = 'src/include/access/gin_private.h'
INDEX = HERE / 'source-index-r1'
assert not INDEX.exists()
env = os.environ.copy()
env.update(GIT_INDEX_FILE=str(INDEX), GIT_OPTIONAL_LOCKS='0',
           GIT_AUTHOR_NAME='root', GIT_AUTHOR_EMAIL='localhost',
           GIT_COMMITTER_NAME='root', GIT_COMMITTER_EMAIL='localhost')


def git(*args, data=None, indexed=True):
    environment = env.copy()
    if not indexed:
        environment.pop('GIT_INDEX_FILE')
    return subprocess.check_output(['git', '-C', str(REPOSITORY), *args],
                                   input=data, env=environment)


def state():
    return [git('rev-parse', 'HEAD', indexed=False),
            git('status', '--porcelain=v1', '-uno', indexed=False)]


before = state()
assert subprocess.run(['git', '-C', str(REPOSITORY), 'show-ref', '--verify',
                       '--quiet', 'refs/heads/' + BRANCH]).returncode == 1
original = (HERE / 'parent-gin_private.h').read_bytes()
assert git('show', PARENT + ':' + PATH) == original
modified = (HERE / 'source' / PATH).read_bytes()
assert hashlib.sha256(modified).hexdigest() == '8feb606e6e825f5e40e6f57c5fc37fe000d88f2aaae011b1a67e2cd8c0862311'
old = b'\tint\t\t\tnrequired;\n\tGinScanEntry *additionalEntries;\n\tint\t\t\tnadditional;'
new = b'\tint\t\t\tnrequired;\n\tint\t\t\tnadditional;\n\tGinScanEntry *additionalEntries;'
assert original.count(old) == 1 and original.replace(old, new) == modified
layout = json.loads((HERE / 'LAYOUT-RESULT-r1.json').read_text())
assert layout['status'] == 'PASS_COMPILE_ONLY_LAYOUT_ASSERTIONS_B_K3_K4'
git('read-tree', PARENT)
blob = git('hash-object', '-w', '--stdin', data=modified).decode().strip()
git('update-index', '--add', '--cacheinfo', '100644,' + blob + ',' + PATH)
tree = git('write-tree').decode().strip()
message = b'''Keep the GIN scan-key counts adjacent

Place nadditional beside nrequired so it occupies the existing alignment
gap before additionalEntries. On the measured 64-bit ABI this reduces
GinScanKeyData from 160 to 152 bytes with the experimental tsquery memo.

This layout experiment leaves cache eligibility, miss policy and callback
arguments unchanged. Compile-only layout assertions pass; backend tests
and performance comparisons have not been run for this variant.
'''
commit = git('commit-tree', tree, '-p', PARENT, data=message).decode().strip()
assert git('diff-tree', '--no-commit-id', '--name-only', '-r', commit).decode().splitlines() == [PATH]
assert git('show', commit + ':' + PATH) == modified
git('update-ref', 'refs/heads/' + BRANCH, commit, '0' * 40)
assert state() == before
(HERE / 'K4-compact-key-over-K3.patch').write_bytes(git('format-patch', '-1', '--stdout', commit))
(HERE / 'K4-full-over-fixedB.diff').write_bytes(git('diff', BASE, commit, '--'))
receipt = dict(status='SOURCE_COMMIT_LOCAL_NOT_PUSHED_COMPILE_ONLY', commit=commit,
               parent=PARENT, fixed_baseline=BASE, branch=BRANCH,
               file=PATH, modified_header_sha256=hashlib.sha256(modified).hexdigest(),
               layout_receipt_sha256=hashlib.sha256((HERE / 'LAYOUT-RESULT-r1.json').read_bytes()).hexdigest(),
               parent_worktree_and_head_unchanged=True, backend_builds=0,
               timing_samples=0, performance_claim=False)
(HERE / 'SOURCE-COMMIT-r1.json').write_text(json.dumps(receipt, indent=2) + '\n')
print(json.dumps(receipt, indent=2))
