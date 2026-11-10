#!/usr/bin/env python3
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
   assert raw.endswith(b'\n');stream.write(raw)
 raw=path.read_bytes();assert len(raw)==item['bytes']and sha(raw)==item['sha256']
manifest=json.loads((a.out_new/'COLLECTION-MANIFEST.json').read_text())
for name,item in manifest['files'].items():
 raw=(a.out_new/name).read_bytes();assert len(raw)==item['bytes']and sha(raw)==item['sha256']
print(json.dumps(dict(status='PASS_EXACT_59_FILE_RESTORE',files=len(manifest['files']),output=str(a.out_new))))
