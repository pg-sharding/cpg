#!/usr/bin/env python3
"""Restore the exact saved evidence; no build, SQL or timing execution."""
import argparse,gzip,hashlib,json,pathlib,shutil
p=argparse.ArgumentParser(description=__doc__);p.add_argument('--manifest',type=pathlib.Path,required=True);p.add_argument('--output',type=pathlib.Path,required=True);a=p.parse_args()
assert not a.output.exists(),'Choose a new restore directory';a.output.mkdir(parents=True)
m=json.loads(a.manifest.read_text());base=a.manifest.parent
for name,entry in m['files'].items():
 rel=pathlib.Path(name);assert not rel.is_absolute() and '..' not in rel.parts
 dest=a.output/rel;dest.parent.mkdir(parents=True,exist_ok=True)
 if entry['kind']=='whole_line_gzip_chunks':
  with dest.open('xb') as out:
   for part in entry['parts']:
    raw=(base/part['path']).read_bytes();assert hashlib.sha256(raw).hexdigest()==part['gzip_sha256']
    text=gzip.decompress(raw);assert hashlib.sha256(text).hexdigest()==part['uncompressed_sha256'] and text.count(b'\n')==part['lines'];out.write(text)
 else:shutil.copy2(base/entry['path'],dest)
 raw=dest.read_bytes();assert len(raw)==entry['bytes'] and hashlib.sha256(raw).hexdigest()==entry['sha256'],name
print(json.dumps({'status':'PASS_EXACT_RESTORE','files':len(m['files']),'output':str(a.output)},indent=2))
