"""Restore exact K3 selected evidence, verifying every original collection binding."""
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
   raw=gzip.decompress(data);assert len(raw)==c['bytes']and sha(raw)==c['sha256']and raw.endswith(b'\n');f.write(raw)
 raw=path.read_bytes();assert len(raw)==item['bytes']and sha(raw)==item['sha256']
count=0
for base,manifest in [('build-qualification','COLLECTION-BUILD-QUAL-K3-r1.json'),('screen','COLLECTION.json')]:
 root=a.out_new/base
 for name,v in json.loads((root/manifest).read_text())['files'].items():
  raw=(root/name).read_bytes();assert len(raw)==v['bytes']and sha(raw)==v['sha256'];count+=1
print(json.dumps(dict(status='PASS_EXACT_ORIGINAL_COLLECTION_RESTORE',files=count,output=str(a.out_new))))
