"""Assemble measured K3 packet without changing any original input or result."""
import gzip
import hashlib
import json
import pathlib
import shutil

HERE = pathlib.Path(__file__).resolve().parent
OUT = HERE / 'publication-r1'
assert not OUT.exists()
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
assert json.loads((HERE / 'ROOT-SCREEN-RECOUNT-K3-r1.json').read_text())['status'] == 'PASS_INDEPENDENT_COMPLETE_RECOUNT'
assert json.loads((HERE / 'ROOT-FINAL-LIVE-K3-r2.json').read_text())['stopped_cluster_lifetimes'] == 17
scaffold = HERE / 'packaging-prep-r1'
spec = json.loads((scaffold / 'MANIFEST-PREPARER.json').read_text())
for name, value in spec['files'].items():
    path = scaffold / name
    assert path.stat().st_size == value['bytes'] and sha(path) == value['sha256'], name
shutil.copytree(scaffold, OUT)
for name in ['README.md', 'email-draft-K3-UNSENT.txt', 'ARTIFACT-REQUIREMENTS.md']:
    (OUT / 'preparer-history').mkdir(exist_ok=True)
    (OUT / name).rename(OUT / 'preparer-history' / name)
def copy(source, relative):
    path = OUT / relative
    assert source.is_file() and not source.is_symlink() and not path.exists(), relative
    path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, path)

for folder, target in [('analysis-cohort0-r1', 'analysis/cohort0'), ('analysis-cohort1-r1', 'analysis/cohort1'),
                       ('independent-qualification-r1', 'qualification-audit-independent'),
                       ('root-qualification-audit-r1', 'qualification-audit-root')]:
    for path in sorted((HERE / folder).rglob('*')):
        if path.is_file():
            copy(path, target + '/' + path.relative_to(HERE / folder).as_posix())
for name in ['FINDINGS-K3-r1.md', 'SUMMARY-ALL-CELLS-K3-r1.json', 'RESULTS-ALL-GROUPS-K3-r1.md',
             'RESULTS-ALL-GROUPS-K3-r1.md.receipt.json', 'SCREEN-INDEPENDENT-AUDIT-r1.json',
             'ROOT-SCREEN-RECOUNT-K3-r1.json', 'ROOT-FINAL-LIVE-K3-r2.json',
             'ROOT-FINAL-LIVE-K3-r1-FAILED.json', 'SMOKE-INDEPENDENT-AUDIT-r1.json',
             'ROOT-LOCAL-SMOKE-REVIEW-K3-r1.json', 'ACTUAL-NORMAL-CODEGEN-REVIEW-r1.json']:
    copy(HERE / name, name)
for name in ['audit-qualification-r1.py', 'audit-screen-independent-K3-r1.py', 'audit-smoke-K3-r1.py']:
    copy(HERE / name, 'reference-inputs/' + name)
for name in ['ROOT-IMPORT-PREPARE-SMOKE-K3-r1.py', 'ROOT-LAUNCH-ACCEPTED-K3-r1.py',
             'final-live-proof-K3-r1.py', 'final-live-proof-K3-r2.py', 'collect-screen-K3-r1.py',
             'render-screen-results-K3-r1.py', 'prepare-publication-K3-r1.py']:
    copy(HERE / name, 'actual-operation-scripts/' + name)
copy(HERE.parent / 'PUBLICATION-REFS-VERIFIED-r1.json', 'SOURCE-REMOTE-REFS-VERIFIED-r1.json')

chunks = {}
limit = 4 * 1024 * 1024
for folder, target in [('evidence-r1', 'build-qualification'), ('screen-collected-r1', 'screen')]:
    for source in sorted((HERE / folder).rglob('*')):
        if not source.is_file():
            continue
        name = target + '/' + source.relative_to(HERE / folder).as_posix()
        assert source.name not in ['PG_VERSION', 'pg_control', 'postmaster.pid', 'regression.diffs', 'regression.out']
        if source.suffix != '.jsonl':
            copy(source, 'evidence/' + name)
            continue
        parts = []
        buf = bytearray()
        def flush():
            if not buf:
                return
            relative = 'raw-chunks/' + name + '.part%03d.gz' % len(parts)
            path = OUT / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(gzip.compress(bytes(buf), mtime=0))
            parts.append(dict(path=relative, compressed_bytes=path.stat().st_size, compressed_sha256=sha(path),
                              bytes=len(buf), sha256=hashlib.sha256(buf).hexdigest()))
            buf.clear()
        for line in source.open('rb'):
            assert line.endswith(b'\n') and len(line) <= limit
            if len(buf) + len(line) > limit:
                flush()
            buf.extend(line)
        flush()
        chunks[name] = dict(bytes=source.stat().st_size, sha256=sha(source), chunks=parts)
(OUT / 'RAW-CHUNKS.json').write_text(json.dumps(dict(status='EXACT_WHOLE_LINE_CHUNKS', chunk_uncompressed_limit=limit, files=chunks), indent=2) + '\n')
restore = '''"""Restore exact K3 selected evidence, verifying every original collection binding."""
import argparse,gzip,hashlib,json,pathlib,shutil
HERE=pathlib.Path(__file__).resolve().parent
p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out-new',type=pathlib.Path,required=True);a=p.parse_args()
assert not a.out_new.exists();shutil.copytree(HERE/'evidence',a.out_new)
sha=lambda b:hashlib.sha256(b).hexdigest()
for name,item in json.loads((HERE/'RAW-CHUNKS.json').read_text())['files'].items():
 path=a.out_new/name;assert not path.exists();path.parent.mkdir(parents=True,exist_ok=True)
 with path.open('xb')as f:
  for c in item['chunks']:
   data=(HERE/c['path']).read_bytes();assert len(data)==c['compressed_bytes']and sha(data)==c['compressed_sha256']
   raw=gzip.decompress(data);assert len(raw)==c['bytes']and sha(raw)==c['sha256']and raw.endswith(b'\\n');f.write(raw)
 raw=path.read_bytes();assert len(raw)==item['bytes']and sha(raw)==item['sha256']
count=0
for base,manifest in [('build-qualification','COLLECTION-BUILD-QUAL-K3-r1.json'),('screen','COLLECTION.json')]:
 root=a.out_new/base
 for name,v in json.loads((root/manifest).read_text())['files'].items():
  raw=(root/name).read_bytes();assert len(raw)==v['bytes']and sha(raw)==v['sha256'];count+=1
print(json.dumps(dict(status='PASS_EXACT_ORIGINAL_COLLECTION_RESTORE',files=count,output=str(a.out_new))))
'''
(OUT / 'restore-raw.py').write_text(restore)
files = [p for p in OUT.rglob('*') if p.is_file()]
assert all(p.stat().st_size < 8 * 1024 * 1024 for p in files)
print(json.dumps(dict(status='ASSEMBLED_NOT_YET_FROZEN', files=len(files), bytes=sum(p.stat().st_size for p in files), raw_streams=len(chunks))))
