"""Root-reviewed exact K3 timing import; finite prepare/smoke only."""
import hashlib
import importlib.util
import json
import os
import pathlib
import resource
import subprocess
import tarfile
import time

R = pathlib.Path('/home/reshke/allfuzz/gin-cache-k3-20261110')
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(R / 'build-r1/build-receipt.json') == '7afacbc4f8f9dbaed6cbd8a095c37b55b16737ac785701d42d0287953bc967f8'
assert sha(R / 'qualification-r1/status.json') == '38ed88489dac9c2b01ee6ac4052bdc8860bbfa61062a5b3d86213f11e448bff3'
assert sha(R / 'qualification-chain-r1.json') == '0decabeae8ab85db65d265d2521247233b06dd918ba47ad30fb2f0e2cf8a39dc'
loader = importlib.util.spec_from_file_location('bc', R / 'inputs/build-harness/common.py')
bc = importlib.util.module_from_spec(loader)
loader.loader.exec_module(bc)
build = bc.checked_build(R / 'build-r1')
assert bc.inventory(pathlib.Path(build['common_source'])) == json.loads((R / 'build-r1/K3_assert-source-inventory.json').read_text())
gate = json.loads((R / 'qualification-r1/status.json').read_text())
assert gate['status'] == 'PASS_ORDINARY_SQL_NATIVE_CACHE_BUDGET_AND_GENERIC_FALLBACK'
assert not gate['cleanup_errors'] and gate['remaining_owned'] == gate['timing_samples'] == 0
assert gate['budget_native_calls'] == 51744 and gate['budget_dispatch_transitions'] == 180
for item in gate['clusters']:
    assert item['stopped'] and not (pathlib.Path(item['data']) / 'postmaster.pid').exists()
    assert not list(pathlib.Path(item['socket']).glob('.s.PGSQL.*'))
    for key in ['pid', 'backend_pid']:
        assert not item.get(key) or not pathlib.Path('/proc', str(item[key])).exists()
compilers = [line for line in subprocess.check_output(['ps', '-eo', 'pid=,comm='], text=True).splitlines()
             if line.split()[-1] in {'cc1', 'cc1plus', 'gcc', 'clang', 'make', 'gmake'}]
assert not compilers and os.getloadavg()[0] < 2.0, (compilers, os.getloadavg())
assert not (R / 'inputs/timing-prep-r1').exists() and not (R / 'timing-r1').exists()
archive = R / 'timing-inputs-K3-r1.tar.gz'
assert sha(archive) == 'a81b7df0c466a69282a5b8fdbb6b40850dc05ae2f20f33209e8f102712fcfd78'
with tarfile.open(archive) as stream:
    members = stream.getmembers()
    assert len(members) == len({m.name for m in members}) == 13
    for item in members:
        name = pathlib.PurePosixPath(item.name)
        assert item.isfile() and name.parts[0] == 'inputs' and not name.is_absolute() and '..' not in name.parts
        assert not (R / name).exists()
    for item in members:
        p = R / item.name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(stream.extractfile(item).read())
manifest = R / 'inputs/TIMING-INPUTS-K3-r1.json'
assert sha(manifest) == '04b31067275d988f2cae6cf16824767ec6c1fab00cb1557d6b8a7f62f803f9d7'
for name, v in json.loads(manifest.read_text())['files'].items():
    p = R / 'inputs' / name
    assert p.stat().st_size == v['bytes'] and sha(p) == v['sha256']
chain = r'''import json,os,pathlib,signal,subprocess,time,traceback
R=pathlib.Path('/home/reshke/allfuzz/gin-cache-k3-20261110')
p=R/'timing-prepare-smoke-chain-r1.json'
s=dict(status='STARTING_PREPARE_SMOKE_ONLY',pid=os.getpid(),started_ns=time.time_ns(),accepted_timing_samples=0)
def save():
 q=p.with_suffix('.tmp');q.write_text(json.dumps(s,indent=2)+'\n');q.replace(p)
def terminate(signum,frame):raise KeyboardInterrupt('termination requested')
signal.signal(signal.SIGTERM,terminate)
try:
 for stage in ['prepare','smoke']:
  s.update(status=stage.upper()+'_RUNNING');save()
  command=['python3','-B',str(R/'inputs/timing-prep-r1/campaign.py'),'--stage',stage,'--build',str(R/'build-r1'),'--qualified',str(R/'qualification-r1'),'--output',str(R/'timing-r1'),'--first-port','46340','--cpu-pairs','0:4,4:0','--environment-label','FRESH_HOST_CLEAN_SCREEN']
  with(R/('timing-'+stage+'-launch-r1.log')).open('xb')as log:
   child=subprocess.Popen(command,cwd=R,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True);s['child_pid']=child.pid;save()
   try:rc=child.wait(timeout=5400)
   except BaseException:
    if child.poll()is None:
     try:os.killpg(child.pid,signal.SIGTERM)
     except ProcessLookupError:pass
     try:child.wait(timeout=480)
     except subprocess.TimeoutExpired:os.killpg(child.pid,signal.SIGKILL);child.wait(timeout=15)
    raise
  assert rc==0,(stage,rc)
  proof=json.loads((R/'timing-r1'/(stage+'-status.json')).read_text())
  assert proof['remaining_owned']==0 and not proof['cleanup_errors']
  assert proof['status']==('PASS_PREPARED_NO_TIMINGS'if stage=='prepare'else'PASS_SMOKE_NEEDS_ROOT_REVIEW')
 s.update(status='PASS_SMOKE_NEEDS_ROOT_REVIEW',finished_ns=time.time_ns())
except BaseException as exc:
 s.update(status='FAILED_PRESERVED',error=repr(exc),traceback=traceback.format_exc());raise
finally:save()
'''
launcher = R / 'root-prepare-smoke-chain-K3-r1.py'
assert not launcher.exists()
launcher.write_text(chain)
resource.setrlimit(resource.RLIMIT_AS, (3000000000, 3000000000))
with (R / 'root-prepare-smoke-launch-K3-r1.log').open('xb') as log:
    child = subprocess.Popen(['python3', '-B', str(launcher)], cwd=R, stdin=subprocess.DEVNULL,
                             stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
receipt = dict(status='ROOT_REVIEWED_K3_PREPARE_SMOKE_ONLY_STARTED', pid=child.pid, started_ns=time.time_ns(),
               archive_sha256=sha(archive), timing_manifest_sha256=sha(manifest),
               gate_status_sha256=sha(R / 'qualification-r1/status.json'),
               load_at_launch=list(os.getloadavg()), active_compilers=compilers,
               smoke_raw=92, accepted_timing_samples=0, environment_label='FRESH_HOST_CLEAN_SCREEN')
(R / 'ROOT-LAUNCH-PREPARE-SMOKE-K3-r1.json').write_text(json.dumps(receipt, indent=2) + '\n')
print(json.dumps(receipt))
