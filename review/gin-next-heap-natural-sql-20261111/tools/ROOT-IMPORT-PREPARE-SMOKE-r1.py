"""Import reviewed synthetic SQL harness; prepare and smoke only after previous Heap SQL stops."""
import hashlib
import importlib.util
import json
import os
import pathlib
import resource
import subprocess
import tarfile
import time

R = pathlib.Path('/home/reshke/allfuzz/gin-heap-selective-natural-20261110')
K = pathlib.Path('/home/reshke/allfuzz/gin-heap-wide-sql-followup-20261110/run-r1')
B = pathlib.Path('/home/reshke/allfuzz/gin-next-c11-bitmap-20261110/or-build')
Q = B.parent / 'oq-r2'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
previous = json.loads((K / 'run-status.json').read_text())
assert previous['status'] == 'PASS_FIXED_SCREEN' and previous['remaining_owned'] == 0 and not previous['cleanup_errors']
assert (previous['raw'], previous['retained'], previous['warm']) == (384, 288, 96)
for item in previous['clusters']:
    assert item['stopped'] and not (pathlib.Path(item['data']) / 'postmaster.pid').exists()
    assert not list(pathlib.Path(item['socket']).glob('.s.PGSQL.*'))
    for key in ('pid', 'backend_pid'):
        assert not item.get(key) or not pathlib.Path('/proc', str(item[key])).exists()
assert sha(B / 'build-receipt.json') == '9569933f83177971adbded4fd448a9f0c809a8c03f7945252ea8f48e52f80388'
assert sha(Q / 'status.json') == '5abb4e1c6111e29ab166148748d94915fcfe036f9b112f4e8fa61ff5614aa3c3'
compilers = [line for line in subprocess.check_output(['ps', '-eo', 'pid=,comm='], text=True).splitlines()
             if len(line.split()) > 1 and line.split()[1] in {'cc1', 'cc1plus', 'gcc', 'clang', 'make', 'gmake'}]
assert not compilers and os.getloadavg()[0] < 2.0, (compilers, os.getloadavg())
assert not (R / 'inputs').exists() and not (R / 'run-r1').exists()
archive = R / 'heap-selective-natural-inputs-r1.tar.gz'
assert sha(archive) == '5fa201054cb54aa239431e18f21b0945d28ebc6b9843e740001ec30c0afcf31d'
with tarfile.open(archive) as stream:
    members = stream.getmembers()
    assert len(members) == len({m.name for m in members}) == 19
    for item in members:
        name = pathlib.PurePosixPath(item.name)
        assert item.isfile() and name.parts[0] == 'inputs' and not name.is_absolute() and '..' not in name.parts
        assert not (R / name).exists()
    for item in members:
        path = R / item.name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(stream.extractfile(item).read())
assert sha(R / 'inputs/INPUTS-r1.json') == '5203fb5282bf1a73efa6f525d495e50c4a87405313474f596b3c42fd09b735d9'
for name, binding in json.loads((R / 'inputs/INPUTS-r1.json').read_text())['files'].items():
    path = R / 'inputs' / name
    assert path.stat().st_size == binding['bytes'] and sha(path) == binding['sha256']
loader = importlib.util.spec_from_file_location('bc', R / 'inputs/build_common.py')
bc = importlib.util.module_from_spec(loader)
loader.loader.exec_module(bc)
build = bc.checked_build(B)
assert bc.inventory(build['common_source']) == json.loads((B / 'Heap_assert-source-inventory.json').read_text())
assert bc.inventory(Q / 'seed') == json.loads((Q / 'seed-manifest.json').read_text())
bc.stopped(pathlib.Path(build['variants']['B']['prefix']), Q / 'seed')
for item in previous['clusters']:
    bc.stopped(item['prefix'], item['data'])
chain = '''import json,os,pathlib,signal,subprocess,time,traceback
R=pathlib.Path('/home/reshke/allfuzz/gin-heap-selective-natural-20261110')
B='/home/reshke/allfuzz/gin-next-c11-bitmap-20261110/or-build'
Q='/home/reshke/allfuzz/gin-next-c11-bitmap-20261110/oq-r2'
K='/home/reshke/allfuzz/gin-heap-wide-sql-followup-20261110/run-r1'
p=R/'prepare-smoke-chain-r1.json'
s=dict(status='STARTING_PREPARE_SMOKE_ONLY',pid=os.getpid(),started_ns=time.time_ns(),accepted_timing_samples=0)
def save():
 t=p.with_suffix('.tmp');t.write_text(json.dumps(s,indent=2)+'\\n');t.replace(p)
def terminate(signum,frame):raise KeyboardInterrupt('termination requested')
signal.signal(signal.SIGTERM,terminate)
try:
 for stage in ['prepare','smoke']:
  s.update(status=stage.upper()+'_RUNNING');save()
  command=['python3','-B',str(R/'inputs/campaign.py'),'--stage',stage,'--build',B,'--qualified',Q,'--previous-heap-run',K,'--output',str(R/'run-r1'),'--first-port','46540','--cpu-pairs','0:4,4:0','--environment-label','FRESH_HOST_CLEAN_SCREEN']
  with(R/(stage+'-launch-r1.log')).open('xb')as log:
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
  proof=json.loads((R/'run-r1'/(stage+'-status.json')).read_text())
  assert proof['remaining_owned']==0 and not proof['cleanup_errors']
  assert proof['status']==('PASS_PREPARED_NO_TIMINGS'if stage=='prepare'else'PASS_SMOKE_NEEDS_ROOT_REVIEW')
 s.update(status='PASS_SMOKE_NEEDS_ROOT_REVIEW',finished_ns=time.time_ns())
except BaseException as exc:
 s.update(status='FAILED_PRESERVED',error=repr(exc),traceback=traceback.format_exc());raise
finally:save()
'''
launcher = R / 'root-prepare-smoke-chain-r1.py'
assert not launcher.exists()
launcher.write_text(chain)
resource.setrlimit(resource.RLIMIT_AS, (3000000000, 3000000000))
with (R / 'root-prepare-smoke-launch-r1.log').open('xb') as log:
    child = subprocess.Popen(['python3', '-B', str(launcher)], cwd=R, stdin=subprocess.DEVNULL,
                             stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
receipt = dict(status='ROOT_REVIEWED_HEAP_SELECTIVE_NATURAL_PREPARE_SMOKE_ONLY_STARTED', pid=child.pid, started_ns=time.time_ns(),
               archive_sha256=sha(archive), previous_Heap_SQL_run_status_sha256=sha(K / 'run-status.json'),
               load_at_launch=list(os.getloadavg()), active_compilers=compilers,
               smoke_raw=24, accepted_timing_samples=0, environment_label='FRESH_HOST_CLEAN_SCREEN')
(R / 'ROOT-LAUNCH-PREPARE-SMOKE-r1.json').write_text(json.dumps(receipt, indent=2) + '\n')
print(json.dumps(receipt))
