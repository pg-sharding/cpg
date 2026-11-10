#!/usr/bin/env python3
"""Assemble short-batch SQL artifacts and exact original Heap parent; no freeze."""
import hashlib
import json
import pathlib
import shutil

HERE=pathlib.Path(__file__).resolve().parent
PARENT=HERE.parent/'or-consistent/or/publication-r1'
OUT=HERE/'publication-r1'
PRIOR=HERE.parent/'heap-selective-natural-20261110/publication-r1'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
read=lambda p:json.loads(p.read_text())
assert not OUT.exists()
assert read(HERE/'ROOT-SCREEN-RECOUNT-r1.json')['numeric_comparisons']==5130
live=read(HERE/'ROOT-FINAL-LIVE-r1.json')
assert live['status']=='PASS_NINE_SHORT_BATCH_SQL_LIFETIMES_STOPPED_AND_HELD_BINDINGS_UNCHANGED'
assert live['stopped_cluster_lifetimes']==9 and not live['active_owned_postgres']
parent_manifest=read(PARENT/'MANIFEST.json')
assert parent_manifest['status']=='FROZEN_AFTER_ROOT_REVIEW'
parent_files={p.relative_to(PARENT).as_posix():p for p in PARENT.rglob('*') if p.is_file()}
assert len(parent_files)==266 and set(parent_files)==set(parent_manifest['files'])|{'MANIFEST.json'}
for name,v in parent_manifest['files'].items():
    p=PARENT/name;assert not p.is_symlink() and p.stat().st_size==v['bytes'] and sha(p)==v['sha256'],name
OUT.mkdir();selected={}
def copy(source,relative,scope='natural-workspace'):
    p=OUT/relative
    assert source.is_file() and not source.is_symlink() and not p.exists()
    p.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,p)
    assert p.read_bytes()==source.read_bytes()
    selected[relative]=dict(scope=scope,source=source.relative_to(PARENT if scope=='historical-parent' else PRIOR if scope=='prior-natural' else HERE.parent if scope=='publication-reference' else HERE).as_posix(),bytes=p.stat().st_size,sha256=sha(p))
for name,p in sorted(parent_files.items()):copy(p,'historical-parent/'+name,'historical-parent')
manifest=read(HERE/'INPUTS-r1.json')
assert sha(HERE/'INPUTS-r1.json')=='b4786b7f3e88fa9d2cd2e6e0714854f4117d1b5f421580aadbb3590cfc673d04'
for name,v in manifest['files'].items():
    p=HERE/name;assert p.stat().st_size==v['bytes'] and sha(p)==v['sha256'];copy(p,'reference-inputs/'+name)
copy(HERE/'INPUTS-r1.json','reference-inputs/INPUTS-r1.json')
copy(HERE/'heap-short-batch-inputs-r1.tar.gz','reference-inputs/heap-short-batch-inputs-r1.tar.gz')
collection=read(HERE/'screen-collected-r1/COLLECTION.json');assert len(collection['files'])==36
for name,v in collection['files'].items():
    p=HERE/'screen-collected-r1'/name;assert p.stat().st_size==v['bytes'] and sha(p)==v['sha256'];copy(p,'evidence/'+name)
copy(HERE/'screen-collected-r1/COLLECTION.json','evidence/COLLECTION.json')
# The original smoke transport receipt is retained separately; its15 payloads
# are byte-identical to their existing copies in the final36-file collection.
smoke=read(HERE/'smoke-collected-r1/COLLECTION.json');assert len(smoke['files'])==15
for name,v in smoke['files'].items():
    assert name in collection['files'] and v==collection['files'][name]
copy(HERE/'smoke-collected-r1/COLLECTION.json','evidence/SMOKE-COLLECTION.json')
for cohort in [0,1]:
    for name in ['absolute.json','pairs.json','status.json']:copy(HERE/f'analysis-cohort{cohort}-r1'/name,f'analysis/cohort{cohort}/'+name)
for name in ['BENCHMARKS-r1.md','BENCHMARKS-r1.receipt.json','FINDINGS.md','email-draft-results-UNSENT.txt',
             'SCREEN-INDEPENDENT-AUDIT-r1.json','SMOKE-INDEPENDENT-AUDIT-r1.json','ROOT-SCREEN-RECOUNT-r1.json',
             'ROOT-LOCAL-SMOKE-REVIEW-r1.json','ROOT-LOCAL-REVIEW-r1.json','ROOT-FINAL-LIVE-r1.json']:
    copy(HERE/name,name)
copy(HERE/'PACKET-README.md','README.md')
for name in ['audit-independent-r1.py','collect-text-r1.py','render-results-r1.py','generate-sql-replay.py','static-check.py',
             'final-live-proof-r1.py','ROOT-IMPORT-PREPARE-SMOKE-r1.py','ROOT-LAUNCH-ACCEPTED-r1.py',
             'prepare-publication-r1.py','replay-analysis.py','LOCAL-TOOLS.json','COLLECTION-ALLOWLIST-r1.json',
             'REPRODUCE.md','replay-batch100.sql']:
    copy(HERE/name,'tools/'+name)
copy(PARENT/'source/code-over-fixed-B.diff','source.diff','historical-parent')
copy(PARENT/'source/code.patch','source.patch','historical-parent')
copy(HERE/'PRIOR-NATURAL-EVIDENCE.json','PRIOR-NATURAL-EVIDENCE.json')
prior=read(HERE/'PRIOR-NATURAL-EVIDENCE.json')
assert sha(PRIOR/'MANIFEST.json')==prior['manifest_sha256']
for name,v in prior['metadata_subset'].items():
    p=PRIOR/name;assert p.stat().st_size==v['bytes'] and sha(p)==v['sha256'];copy(p,'prior-natural-evidence/'+name,'prior-natural')
for name in ['HEAP-NATURAL-SQL-REMOTE-VERIFIED-r1.json','HEAP-NATURAL-SQL-S3-RECEIPT-r1.json']:
    copy(HERE.parent/name,'prior-natural-evidence/'+name,'publication-reference')
# Relocated fresh-build/read-only SQL instructions; original preparer document
# remains byte-exact in tools/REPRODUCE.md and its LOCAL-TOOLS binding.
text=(HERE/'REPRODUCE.md').read_text()
text=text.replace('README.md gives the exact held-artifact staged prepare/smoke/review/run commands.',
                  'reference-inputs/README.md gives the exact held-artifact staged prepare/smoke/review/run commands.')
text=text.replace('PARENT=/absolute/path/to/unchanged/historical-Heap-packet','PARENT="$PACKET/historical-parent"')
text=text.replace('"$PACKET/generate-sql-replay.py"','"$PACKET/tools/generate-sql-replay.py"')
text=text.replace('"$PACKET/cases.json"','"$PACKET/reference-inputs/cases.json"')
text=text.replace('"$PACKET/WORKLOAD.json"','"$PACKET/reference-inputs/WORKLOAD.json"')
(OUT/'REPRODUCE.md').write_text(text)
selected['REPRODUCE.md']=dict(scope='relocated-document-from-natural-workspace',source='REPRODUCE.md',source_sha256=sha(HERE/'REPRODUCE.md'),bytes=(OUT/'REPRODUCE.md').stat().st_size,sha256=sha(OUT/'REPRODUCE.md'))
for name,v in selected.items():
    p=OUT/name;assert p.stat().st_size==v['bytes'] and sha(p)==v['sha256']
assert all(not p.is_symlink() and '__pycache__' not in p.parts and p.stat().st_size<8*1024*1024 for p in OUT.rglob('*') if p.is_file())
proof=dict(status='ASSEMBLED_FOR_ROOT_REVIEW_NOT_FROZEN',historical_parent_files=266,frozen_reference_inputs=19,collected_payloads=36,analysis_json=6,
           selected=selected,production_source_changes=0,no_recursive_forcedwide_packet=True,all_selected_hashes_verified=True,
           no_PGDATA_executables_shared_libraries_or_full_logs=True)
(OUT/'ASSEMBLY-SELECTION.json').write_text(json.dumps(proof,indent=2)+'\n')
print(json.dumps(dict(status=proof['status'],files=sum(p.is_file() for p in OUT.rglob('*')),selected_files=len(selected),bytes=sum(p.stat().st_size for p in OUT.rglob('*') if p.is_file()))))
