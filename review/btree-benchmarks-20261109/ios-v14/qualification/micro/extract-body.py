#!/usr/bin/env python3
"""Extract the unchanged actual _bt_returnitem definition, not a reimplementation."""
from pathlib import Path
import hashlib,json,sys

if len(sys.argv)!=4:
    raise SystemExit('usage: extract-body.py source-root output-header evidence-json')
root,output,evidence=map(Path,sys.argv[1:])
path=root/'src/backend/access/nbtree/nbtsearch.c'
raw=path.read_bytes();text=raw.decode();start=text.rindex('static inline void\n_bt_returnitem(')
brace=text.index('{',start);depth=1;end=brace+1
while depth:
    if text[end]=='{':depth+=1
    if text[end]=='}':depth-=1
    end+=1
body=text[start:end]+'\n'
output.parent.mkdir(parents=True,exist_ok=True);output.write_text(body)
evidence.write_text(json.dumps({'source':str(path),'source_sha256':hashlib.sha256(raw).hexdigest(),
    'body_sha256':hashlib.sha256(body.encode()).hexdigest(),'bytes':len(body.encode()),
    'extraction':'Exact static inline definition, from signature through closing brace; no rewriting.'},indent=2)+'\n')
