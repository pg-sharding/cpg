"""Collect bounded synthetic heap SQL proof only after that finite stage stops."""
import argparse
import hashlib
import json
import pathlib
import subprocess
import time

HERE = pathlib.Path(__file__).resolve().parent
R = '/home/reshke/allfuzz/gin-heap-wide-sql-followup-20261110'
p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--stage', choices=['smoke', 'run'], required=True)
p.add_argument('--out-new', type=pathlib.Path, required=True)
a = p.parse_args()
names = ['ROOT-LAUNCH-PREPARE-SMOKE-r1.json', 'prepare-smoke-chain-r1.json',
         'run-r1/prepare-status.json', 'run-r1/smoke-status.json', 'run-r1/freeze.json',
         'run-r1/seed-inventory.json', 'run-r1/runtime-smoke.json']
for label in ['smoke'] + ([] if a.stage == 'smoke' else ['cohort0', 'cohort1']):
    names += ['run-r1/' + label + '/' + n for n in
              ['status.json', 'raw.jsonl', 'literal.jsonl', 'oracles.json',
               'B-backend.json', 'T-backend.json', 'Heap-backend.json']]
if a.stage == 'run':
    names += ['run-r1/run-status.json', 'run-r1/runtime-cohort0.json', 'run-r1/runtime-cohort1.json',
              'ROOT-SMOKE-REVIEW-r1.json', 'ROOT-LAUNCH-ACCEPTED-r1.json']
assert len(set(names)) == len(names)
script = '''import pathlib,json,hashlib
root=pathlib.Path(ROOT_VALUE)
stage=STAGE_VALUE
status=json.loads((root/'run-r1'/(stage+'-status.json')).read_text())
assert status['status']==('PASS_SMOKE_NEEDS_ROOT_REVIEW'if stage=='smoke'else'PASS_FIXED_SCREEN')
assert status['remaining_owned']==0 and not status['cleanup_errors']
assert len(status['clusters'])==(3 if stage=='smoke' else 6)
for item in status['clusters']:
 assert item['stopped'] and not(pathlib.Path(item['data'])/'postmaster.pid').exists()
 assert not list(pathlib.Path(item['socket']).glob('.s.PGSQL.*'))
 for key in ['pid','backend_pid']:
  assert not item.get(key) or not pathlib.Path('/proc',str(item[key])).exists()
result={}
for name in NAMES_VALUE:
 p=root/name
 assert p.is_file()and not p.is_symlink()and p.stat().st_size<20*1024*1024
 data=p.read_bytes();result[name]=dict(text=data.decode(),bytes=len(data),sha256=hashlib.sha256(data).hexdigest())
print(json.dumps(result))
'''.replace('ROOT_VALUE', repr(R)).replace('STAGE_VALUE', repr(a.stage)).replace('NAMES_VALUE', repr(names))
assert not a.out_new.exists()
result = subprocess.check_output(['/usr/bin/ssh', '-A', '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=10',
                                  'reshke@158.160.212.50', 'python3 -B -'], input=script.encode(), timeout=120)
values = json.loads(result)
assert set(values) == set(names)
a.out_new.mkdir()
files = {}
for name, item in values.items():
    path = a.out_new / name
    data = item.pop('text').encode()
    assert len(data) == item['bytes'] and hashlib.sha256(data).hexdigest() == item['sha256']
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    files[name] = item
receipt = dict(status='PASS_EXACT_SELECTED_TEXT_AFTER_STOPPED_STAGE', stage=a.stage, files=files,
               remote=R, collected_ns=time.time_ns(), no_PGDATA_executables_or_full_logs=True)
(a.out_new / 'COLLECTION.json').write_text(json.dumps(receipt, indent=2) + '\n')
print(json.dumps(dict(status=receipt['status'], stage=a.stage, files=len(files), bytes=sum(v['bytes'] for v in files.values()))))
