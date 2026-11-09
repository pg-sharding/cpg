#!/usr/bin/env python3
"""Measure the actual installed private scan-state layout without a server."""
import json
from pathlib import Path
import re
import shlex
import subprocess
from common import ROOT,Runtime,sha,save

out=ROOT/'layout-r1'
out.mkdir()
runtime=Runtime(out)
rows={}
for role in ['B','R','C','D','C_assert','D_assert']:
    prefix=runtime.prefix(role)
    get=lambda name:subprocess.check_output([str(prefix/'bin/pg_config'),'--'+name],text=True).strip()
    source=out/(role+'.c')
    source.write_text('#include "postgres.h"\n#include "access/gist_private.h"\n'
                      'char scan_state_size[sizeof(GISTScanOpaqueData)];\n'
                      'char distances_offset[offsetof(GISTScanOpaqueData, distances)];\n'
                      'char page_data_offset[offsetof(GISTScanOpaqueData, pageData)];\n'+
                      ('char box_candidate_offset[offsetof(GISTScanOpaqueData, boxBatchCandidate)];\n' if role.startswith('C') else ''))
    obj=out/(role+'.o')
    runtime.run(role,['gcc',*shlex.split(get('cflags')),*shlex.split(get('cppflags')),
                      '-I'+str(prefix/'include/postgresql/server'),'-c',source,'-o',obj],role+'-compile.log')
    symbols=subprocess.check_output(['nm','-S','--defined-only',str(obj)],text=True)
    (out/(role+'-symbols.txt')).write_text(symbols)
    rows[role]={m[2]:int(m[1],16) for m in re.finditer(r'^[0-9a-f]+ ([0-9a-f]+) [BD] (\w+)$',symbols,re.M)}
    assert set(rows[role])>={'scan_state_size','distances_offset','page_data_offset'}
assert len({tuple(row[n] for n in ['scan_state_size','distances_offset','page_data_offset']) for row in rows.values()})==1
save(out/'receipt.json',{'status':'PASS_UNCHANGED_STATE_SIZE_AND_EXISTING_OFFSETS','roles':rows})
print(json.dumps(rows,indent=2))
