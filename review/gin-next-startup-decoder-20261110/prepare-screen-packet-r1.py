#!/usr/bin/env python3
"""Make a new provisional public/synthetic packet; never change collected inputs."""
import argparse
import gzip
import hashlib
import json
import pathlib
import shutil

HERE=pathlib.Path(__file__).resolve().parent
LIMIT=4*1024*1024

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--out-new',type=pathlib.Path,required=True)
    a=p.parse_args();out=a.out_new.resolve();out.mkdir()
    audit=json.loads((HERE/'INDEPENDENT-MATH-AUDIT-shared84-r1.json').read_text())
    assert audit['status']=='PASS_INDEPENDENT_COMPLETE_RECOUNT'
    def copy(source,target):
        target=out/target;assert not target.exists() and source.is_file() and not source.is_symlink()
        target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,target)
    for folder in ['build-harness','build-source','qualification','screen','patches']:
        for source in sorted((HERE/folder).rglob('*')):
            if source.is_file() and '__pycache__' not in source.parts and source.name not in {'S1-over-fixed-B.patch','D1-over-fixed-B.patch'}:
                copy(source,source.relative_to(HERE))
    roots=['BUILD-INPUTS-r1.json','QUALIFICATION-INPUTS-r1.json','SCREEN-INPUTS-r1.json',
           'SOURCE-IDENTITY-CORRECTION-r1.json','SOURCE-REVIEW.md','SCREEN-REPRODUCE.md',
           'INDEPENDENT-MATH-AUDIT-shared84-r1.json','AUDIT-RUNTIME-META-shared84-r1.json',
           'BENCHMARKS-shared84-r1.md','BENCHMARKS-shared84-r1.md.receipt.json','FINDINGS-shared84-r1.md',
           'ROOT-FINAL-LIVE-r1.json','PACKET-FINAL-LIVE-BINDING-r1.json',
           'email-draft-shared84-r1-UNSENT.txt','audit-screen-independent-r1.py','render-screen-results-r1.py',
           'AUDITOR-STATIC-r1.json','prepare-screen-packet-r1.py',
           'build-inputs-r1.tar.gz','qualification-inputs-r1.tar.gz','screen-inputs-r1.tar.gz']
    for name in roots:copy(HERE/name,name)
    historical = out / 'SCREEN-REPRODUCE.md'
    historical.write_text('Historical prospective instructions, retained below. The six builds/gate and full screen subsequently completed; current measured status and limitations are in FINDINGS-shared84-r1.md and REPRODUCE.md.\n\n' + historical.read_text())
    copy(HERE.parent/'SOURCE-PUBLICATION-r1.json','SOURCE-PUBLICATION-r1.json')
    for name,target in [('PACKET-README-shared84-r1.md','README.md'),('REPRODUCE-shared84-r1.md','REPRODUCE.md'),('bounded-exec.py','bounded-exec.py')]:copy(HERE/name,target)
    for source in sorted(HERE.glob('PRIOR-ART-*.json')):copy(source,'prior-art/'+source.name)
    copy(HERE/'prior-art-output-size-0005.txt','prior-art/prior-art-output-size-0005.txt')
    cache=HERE.parent/'or-consistent/cache'
    for name in ['SOURCE.json','cache-v1-over-fixed-B.diff','cache-v1-over-fixed-B.patch',
                 'NATIVE-STATUS-r1-001.json','PROBE-STATUS-r2-001.json','COMPILE-FAILURE-r1.txt',
                 'CONTRACT-REVIEW.md','PRIOR-ART-HEIKKI2014.json',
                 'AUTO-REVIEW-REJECTION-NATIVE-r1.json','AUTO-REVIEW-REJECTION-NATIVE-LAUNCH-r1.json',
                 'ROOT-PAYLOAD-REVIEW-NATIVE-r1.json','ROOT-TRANSFER-NATIVE-r1.json','ROOT-LAUNCH-NATIVE-r1.json']:
        copy(cache/name,'cache-untimed-evidence/'+name)
    for folder in ['native-preflight-r1','probe-r2']:
        for source in sorted((cache/folder).rglob('*')):
            if source.is_file() and '__pycache__' not in source.parts:
                copy(source,'cache-untimed-evidence/'+source.relative_to(cache).as_posix())
    for cohort in [0,1]:
        for source in sorted((HERE/f'analysis-shared84-r1-cohort{cohort}').glob('*.json')):
            copy(source,f'analysis/cohort{cohort}/'+source.name)
    collection=HERE/'final-collection-r1'
    original=json.loads((collection/'COLLECTION-MANIFEST.json').read_text())
    chunked={}
    for source in sorted(collection.rglob('*')):
        if not source.is_file():continue
        name=source.relative_to(collection).as_posix()
        if source.suffix!='.jsonl':
            copy(source,'evidence/final-collection-r1/'+name);continue
        chunks=[];buffer=bytearray();index=0
        def flush():
            nonlocal buffer,index
            if not buffer:return
            rel=f'raw-chunks/{name}.part{index:03d}.gz';target=out/rel;target.parent.mkdir(parents=True,exist_ok=True)
            target.write_bytes(gzip.compress(bytes(buffer),mtime=0))
            chunks.append(dict(path=rel,compressed_bytes=target.stat().st_size,compressed_sha256=sha(target),bytes=len(buffer),sha256=hashlib.sha256(buffer).hexdigest()))
            buffer=bytearray();index+=1
        with source.open('rb')as stream:
            for line in stream:
                assert len(line)<=LIMIT and line.endswith(b'\n')
                if len(buffer)+len(line)>LIMIT:flush()
                buffer.extend(line)
        flush()
        chunked[name]=dict(bytes=source.stat().st_size,sha256=sha(source),chunks=chunks)
        assert original['files'][name]['bytes']==source.stat().st_size and original['files'][name]['sha256']==sha(source)
    (out/'RAW-CHUNKS.json').write_text(json.dumps(dict(status='EXACT_WHOLE_LINE_CHUNKS',chunk_uncompressed_limit=LIMIT,files=chunked),indent=2)+'\n')
    restore='''#!/usr/bin/env python3
"""Restore exact collected text/JSON/JSONL into a NEW local directory."""
import argparse,gzip,hashlib,json,pathlib,shutil
HERE=pathlib.Path(__file__).resolve().parent
p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out-new',type=pathlib.Path,required=True);a=p.parse_args()
assert not a.out_new.exists()
shutil.copytree(HERE/'evidence/final-collection-r1',a.out_new)
sha=lambda b:hashlib.sha256(b).hexdigest()
spec=json.loads((HERE/'RAW-CHUNKS.json').read_text())
for name,item in spec['files'].items():
 path=a.out_new/name;assert not path.exists();path.parent.mkdir(parents=True,exist_ok=True)
 with path.open('xb')as stream:
  for chunk in item['chunks']:
   data=(HERE/chunk['path']).read_bytes();assert len(data)==chunk['compressed_bytes']and sha(data)==chunk['compressed_sha256']
   raw=gzip.decompress(data);assert len(raw)==chunk['bytes']and sha(raw)==chunk['sha256']
   assert raw.endswith(b'\\n');stream.write(raw)
 raw=path.read_bytes();assert len(raw)==item['bytes']and sha(raw)==item['sha256']
manifest=json.loads((a.out_new/'COLLECTION-MANIFEST.json').read_text())
for name,item in manifest['files'].items():
 raw=(a.out_new/name).read_bytes();assert len(raw)==item['bytes']and sha(raw)==item['sha256']
print(json.dumps(dict(status='PASS_EXACT_59_FILE_RESTORE',files=len(manifest['files']),output=str(a.out_new))))
'''
    (out/'restore-raw.py').write_text(restore)
    (out/'PROVISIONAL-NOT-FROZEN.txt').write_text('Prepared locally after complete run/analyzer/independent audit and root final live inventory PASS. Root final review and publication manifest/freeze remain pending. Do not present this as final publication.\n')
    paths=[p for p in out.rglob('*')if p.is_file()]
    assert all(p.stat().st_size<8*1024*1024 for p in paths)
    receipt=dict(status='PROVISIONAL_PACKET_PREPARED',output=str(out),files=len(paths),bytes=sum(p.stat().st_size for p in paths),largest_file=max((p.stat().st_size,p.relative_to(out).as_posix())for p in paths),raw_streams=len(chunked),raw_chunks=sum(len(v['chunks'])for v in chunked.values()),independent_audit_sha256=sha(HERE/'INDEPENDENT-MATH-AUDIT-shared84-r1.json'),source_inputs_unchanged=True,final_freeze=False)
    (HERE/'PACKET-PREPARER-REVIEW-shared84-r1.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt))

if __name__=='__main__':main()
