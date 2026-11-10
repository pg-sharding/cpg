#!/usr/bin/env python3
"""Offline relocated exact analysis/audit/table replay, without PG or networking."""
import argparse
import hashlib
import json
import pathlib
import shutil
import subprocess
import sys


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--packet',type=pathlib.Path,required=True)
    p.add_argument('--out-new',type=pathlib.Path,required=True)
    a=p.parse_args();packet=a.packet.resolve();out=a.out_new.resolve()
    assert not out.exists() and out!=packet and packet not in out.parents
    sha=lambda f:hashlib.sha256(f.read_bytes()).hexdigest()
    ref=packet/'reference-inputs'
    manifest=json.loads((ref/'INPUTS-r1.json').read_text())
    assert sha(ref/'INPUTS-r1.json')=='5203fb5282bf1a73efa6f525d495e50c4a87405313474f596b3c42fd09b735d9'
    for name,v in manifest['files'].items():
        f=ref/name;assert not f.is_symlink() and f.stat().st_size==v['bytes'] and sha(f)==v['sha256']
    collection=json.loads((packet/'evidence/COLLECTION.json').read_text())
    assert len(collection['files'])==36
    for name,v in collection['files'].items():
        f=packet/'evidence'/name;assert f.stat().st_size==v['bytes'] and sha(f)==v['sha256']
    out.mkdir();comparisons={}
    for cohort in [0,1]:
        dest=out/f'analysis-cohort{cohort}-r1'
        subprocess.run([sys.executable,'-B',str(ref/'analyze.py'),str(packet/f'evidence/run-r1/cohort{cohort}'),str(dest)],check=True,timeout=60)
        for name in ['absolute.json','pairs.json','status.json']:
            original=packet/f'analysis/cohort{cohort}'/name
            assert (dest/name).read_bytes()==original.read_bytes()
            comparisons[f'cohort{cohort}/{name}']=sha(dest/name)
    audit=out/'SCREEN-INDEPENDENT-AUDIT-r1.json'
    subprocess.run([sys.executable,'-B',str(packet/'tools/audit-independent-r1.py'),'--inputs',str(ref),'--workload',str(ref/'WORKLOAD.json'),'--results',str(packet/'evidence/run-r1'),'--mode','screen','--analysis0',str(out/'analysis-cohort0-r1'),'--analysis1',str(out/'analysis-cohort1-r1'),'--out-new',str(audit)],check=True,timeout=60)
    result=json.loads(audit.read_text());assert result['numeric_comparisons']==8208 and result['raw']==384
    assert audit.read_bytes()==(packet/'SCREEN-INDEPENDENT-AUDIT-r1.json').read_bytes()
    shutil.copy2(ref/'cases.json',out/'cases.json')
    subprocess.run([sys.executable,'-B',str(packet/'tools/render-results-r1.py'),'--root',str(out),'--out-new',str(out/'BENCHMARKS-r1.md')],check=True,timeout=60)
    assert (out/'BENCHMARKS-r1.md').read_bytes()==(packet/'BENCHMARKS-r1.md').read_bytes()
    proof=dict(status='PASS_OFFLINE_RELOCATED_REPLAY_NO_NEW_RUNTIME',analysis_json_byte_exact=comparisons,independent_numeric_comparisons=8208,independent_audit_byte_exact=True,table_byte_exact=True,input_manifest_sha256=sha(ref/'INPUTS-r1.json'),audit_sha256=sha(audit),table_sha256=sha(out/'BENCHMARKS-r1.md'),PostgreSQL_VM_network_compiler_executed=False)
    (out/'OFFLINE-REPLAY.json').write_text(json.dumps(proof,indent=2)+'\n');print(json.dumps(proof))


if __name__=='__main__':main()
