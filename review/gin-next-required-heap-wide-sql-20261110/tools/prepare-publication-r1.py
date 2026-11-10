"""Assemble new SQL follow-up beside an unchanged complete historical parent."""
import hashlib
import json
import pathlib
import shutil

HERE = pathlib.Path(__file__).resolve().parent
PARENT = HERE.parent / 'or-consistent/or/publication-r1'
OUT = HERE / 'publication-r1'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
assert not OUT.exists()
assert json.loads((HERE / 'ROOT-SCREEN-RECOUNT-r1.json').read_text())['numeric_comparisons'] == 8208
assert json.loads((HERE / 'ROOT-FINAL-LIVE-r1.json').read_text())['stopped_cluster_lifetimes'] == 9
original = json.loads((PARENT / 'MANIFEST.json').read_text())
assert original['status'] == 'FROZEN_AFTER_ROOT_REVIEW'
for name, value in original['files'].items():
    path = PARENT / name
    assert path.stat().st_size == value['bytes'] and sha(path) == value['sha256'], name
OUT.mkdir()
shutil.copytree(PARENT, OUT / 'historical-parent')
def copy(source, relative):
    path = OUT / relative
    assert source.is_file() and not source.is_symlink() and not path.exists(), relative
    path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, path)
manifest = json.loads((HERE / 'INPUTS-r1.json').read_text())
for name, value in manifest['files'].items():
    source = HERE / name
    assert source.stat().st_size == value['bytes'] and sha(source) == value['sha256']
    copy(source, 'reference-inputs/' + name)
copy(HERE / 'INPUTS-r1.json', 'reference-inputs/INPUTS-r1.json')
for path in sorted((HERE / 'screen-collected-r1').rglob('*')):
    if path.is_file():
        copy(path, 'evidence/' + path.relative_to(HERE / 'screen-collected-r1').as_posix())
for cohort in [0, 1]:
    for path in sorted((HERE / f'analysis-cohort{cohort}-r1').glob('*.json')):
        copy(path, f'analysis/cohort{cohort}/' + path.name)
for name in ['BENCHMARKS-r1.md', 'BENCHMARKS-r1.receipt.json', 'FINDINGS.md',
             'email-draft-results-UNSENT.txt', 'REPRODUCE-SQL.md',
             'SCREEN-INDEPENDENT-AUDIT-r1.json', 'ROOT-SCREEN-RECOUNT-r1.json',
             'SMOKE-INDEPENDENT-AUDIT-r1.json', 'ROOT-LOCAL-SMOKE-REVIEW-r1.json',
             'ROOT-LOCAL-REVIEW-r1.json', 'ROOT-FINAL-LIVE-r1.json']:
    copy(HERE / name, name)
copy(HERE / 'PACKET-README.md', 'README.md')
for name in ['audit-independent-r1.py', 'AUDITOR-README-r1.md', 'AUDITOR-STATIC-r1.json',
             'render-results-r1.py', 'collect-text-r1.py', 'final-live-proof-r1.py',
             'ROOT-IMPORT-PREPARE-SMOKE-r1.py', 'ROOT-LAUNCH-ACCEPTED-r1.py', 'prepare-publication-r1.py',
             'generate-sql-replay.py']:
    copy(HERE / name, 'tools/' + name)
copy(PARENT / 'source/code-over-fixed-B.diff', 'required-entry-heap.diff')
copy(PARENT / 'source/code.patch', 'required-entry-heap.patch')
copy(HERE.parent / 'CACHE-K3-REMOTE-VERIFIED-r1.json', 'separate-K3/REMOTE-VERIFIED.json')
copy(HERE.parent / 'CACHE-K3-S3-RECEIPT-r1.json', 'separate-K3/S3-RECEIPT.json')
diagnostic = HERE.parent / 'cache-k3-qualification-20261110/dispatcher-diagnostic-prep-r1'
for name, value in json.loads((diagnostic / 'MANIFEST.json').read_text())['files'].items():
    path = diagnostic / name
    assert path.stat().st_size == value['bytes'] and sha(path) == value['sha256']
shutil.copytree(diagnostic, OUT / 'followup-source-preparations/K3-dispatch-diagnostic')
files = [p for p in OUT.rglob('*') if p.is_file()]
assert all(p.stat().st_size < 8 * 1024 * 1024 for p in files)
assert all('__pycache__' not in p.parts and not p.is_symlink() for p in files)
print(json.dumps(dict(status='ASSEMBLED_NOT_YET_FROZEN', files=len(files), bytes=sum(p.stat().st_size for p in files))))
