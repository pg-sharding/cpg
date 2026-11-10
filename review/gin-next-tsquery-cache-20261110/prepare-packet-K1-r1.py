#!/usr/bin/env python3
"""Prepare new provisional K1 artifacts; preserve all frozen/collected inputs."""
import argparse
import gzip
import hashlib
import json
import pathlib
import shutil
HERE=pathlib.Path(__file__).resolve().parent
LIMIT=4*1024*1024
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out-new',type=pathlib.Path,required=True);a=p.parse_args()
 out=a.out_new.resolve();out.mkdir()
 assert json.loads((HERE/'INDEPENDENT-MATH-AUDIT-K1-r1.json').read_text())['status']=='PASS_INDEPENDENT_COMPLETE_RECOUNT'
 proof=HERE/'ROOT-FINAL-LIVE-K1-r1.json';assert sha(proof)=='16e586363f7c85cf6bb66bb0a5e5c2ba4b322f9bfcbfb6310cfa38c56ae00b27'
 live=json.loads(proof.read_text());assert live['status']=='PASS_ROOT_FINAL_LIVE_K1_BINDINGS'
 assert live['source_files']==7726 and live['installed_prefixes']==3 and live['stopped_cluster_lifetimes']==13
 collection=HERE/'final-collected-K1-r1'
 for field,name in [('build_receipt_sha256','build-r1/build-receipt.json'),('run_status_sha256','screen-r1/run-status.json'),('freeze_sha256','screen-r1/freeze.json'),('qualification_status_sha256','qualification-r1/status.json')]:assert live[field]==sha(collection/name)
 def copy(source,target):
  target=out/target;assert source.is_file()and not source.is_symlink()and not target.exists()
  target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,target)
 for folder in ['full-build-harness-r1','full-build-source-r1','full-qualification-r1','screen','analysis-tools-K1-r2','source']:
  for source in sorted((HERE/folder).rglob('*')):
   if source.is_file()and'__pycache__'not in source.parts:copy(source,source.relative_to(HERE))
 names=['static-check-full-r1.py','SOURCE.json','cache-v1-over-fixed-B.diff','cache-v1-over-fixed-B.patch','FULL-BACKEND-INPUTS-r1.json','FULL-BACKEND-PAYLOAD-r1.json','FULL-STATIC-r1.json','FULL-PAYLOAD-AUDIT-r1.json','FULL-BACKEND-REPRODUCE-r1.md','SCREEN-INPUTS-K1-r1.json','SCREEN-PAYLOAD-K1-r1.json','SCREEN-IMPORTER-STATIC-K1-r1.json','SCREEN-REPRODUCE-K1-r1.md','full-backend-inputs-r1.tar.gz','screen-inputs-K1-r1.tar.gz','INDEPENDENT-MATH-AUDIT-K1-r1.json','AUDIT-RUNTIME-META-K1-r1.json','BENCHMARKS-K1-r1.md','BENCHMARKS-K1-r1.md.receipt.json','FINDINGS-K1-r1.md','email-draft-K1-r1-UNSENT.txt','ROOT-FINAL-LIVE-K1-r1.json','ANALYZER-FAILURE-K1-r1.json','ANALYZER-K1-r2.diff','ANALYZER-K1-r2.json','AUDITOR-STATIC-K1-r1.json','SMOKE-AUDIT-K1-r1.json','SMOKE-LOSSY-CONTROL-K1-r1.json','audit-smoke-K1-r1.py','audit-screen-independent-K1-r1.py','render-screen-results-K1-r1.py','prepare-packet-K1-r1.py','PRIOR-ART-HEIKKI2014.json','CONTRACT-REVIEW.md','PROBE-STATUS-r2-001.json']
 for name in names:copy(HERE/name,name)
 copy(HERE.parents[1]/'SOURCE-PUBLICATION-r1.json','SOURCE-PUBLICATION-r1.json')
 copy(HERE.parents[1]/'startup-decoder/bounded-exec.py','bounded-exec.py')
 for name,target in [('PACKET-README-K1-r1.md','README.md'),('REPRODUCE-K1-r1.md','REPRODUCE.md')]:copy(HERE/name,target)
 for cohort in [0,1]:
  for source in sorted((HERE/f'analysis-shared84-K1-r2-cohort{cohort}').glob('*.json')):copy(source,f'analysis/cohort{cohort}/'+source.name)
 manifest=json.loads((collection/'COLLECTION.json').read_text());assert len(manifest['files'])==73
 chunks={}
 for source in sorted(collection.rglob('*')):
  if not source.is_file():continue
  name=source.relative_to(collection).as_posix()
  if source.suffix!='.jsonl':copy(source,'evidence/final-collected-K1-r1/'+name);continue
  parts=[];buffer=bytearray();index=0
  def flush():
   nonlocal buffer,index
   if not buffer:return
   path=f'raw-chunks/{name}.part{index:03d}.gz';target=out/path;target.parent.mkdir(parents=True,exist_ok=True)
   target.write_bytes(gzip.compress(bytes(buffer),mtime=0))
   parts.append(dict(path=path,compressed_bytes=target.stat().st_size,compressed_sha256=sha(target),bytes=len(buffer),sha256=hashlib.sha256(buffer).hexdigest()))
   buffer=bytearray();index+=1
  with source.open('rb')as stream:
   for line in stream:
    assert line.endswith(b'\n')and len(line)<=LIMIT
    if len(buffer)+len(line)>LIMIT:flush()
    buffer.extend(line)
  flush()
  chunks[name]=dict(bytes=source.stat().st_size,sha256=sha(source),chunks=parts)
  assert manifest['files'][name]['sha256']==sha(source)
 (out/'RAW-CHUNKS.json').write_text(json.dumps(dict(status='EXACT_WHOLE_LINE_CHUNKS',chunk_uncompressed_limit=LIMIT,files=chunks),indent=2)+'\n')
 restore='''#!/usr/bin/env python3
"""Restore exact already measured text/JSON/JSONL into a NEW local directory."""
import argparse,gzip,hashlib,json,pathlib,shutil
HERE=pathlib.Path(__file__).resolve().parent
p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out-new',type=pathlib.Path,required=True);a=p.parse_args();assert not a.out_new.exists()
shutil.copytree(HERE/'evidence/final-collected-K1-r1',a.out_new)
sha=lambda b:hashlib.sha256(b).hexdigest()
spec=json.loads((HERE/'RAW-CHUNKS.json').read_text())
for name,item in spec['files'].items():
 path=a.out_new/name;assert not path.exists();path.parent.mkdir(parents=True,exist_ok=True)
 with path.open('xb')as stream:
  for chunk in item['chunks']:
   data=(HERE/chunk['path']).read_bytes();assert len(data)==chunk['compressed_bytes']and sha(data)==chunk['compressed_sha256']
   raw=gzip.decompress(data);assert len(raw)==chunk['bytes']and sha(raw)==chunk['sha256']and raw.endswith(b'\\n');stream.write(raw)
 raw=path.read_bytes();assert len(raw)==item['bytes']and sha(raw)==item['sha256']
manifest=json.loads((a.out_new/'COLLECTION.json').read_text())
for name,item in manifest['files'].items():
 raw=(a.out_new/name).read_bytes();assert len(raw)==item['bytes']and sha(raw)==item['sha256']
print(json.dumps(dict(status='PASS_EXACT_73_FILE_RESTORE',files=len(manifest['files']),output=str(a.out_new))))
'''
 (out/'restore-raw.py').write_text(restore)
 (out/'PROVISIONAL-NOT-FROZEN.txt').write_text('Completed K1 run, corrected local analyzer, independent audit and root final-live checks PASS. All negatives preserved. Root independent math/publication review and final manifest/freeze remain pending. No new timings.\n')
 files=[p for p in out.rglob('*')if p.is_file()];assert all(p.stat().st_size<8*1024*1024 for p in files)
 receipt=dict(status='PROVISIONAL_K1_PACKET_PREPARED_NOT_FROZEN',packet=str(out),files=len(files),bytes=sum(p.stat().st_size for p in files),largest_file=max((p.stat().st_size,p.relative_to(out).as_posix())for p in files),raw_streams=len(chunks),chunks=sum(len(v['chunks'])for v in chunks.values()),root_final_live_sha256=sha(proof),timing_samples_added=0)
 (HERE/'PACKET-PREPARER-REVIEW-K1-r1.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt))
if __name__=='__main__':main()
