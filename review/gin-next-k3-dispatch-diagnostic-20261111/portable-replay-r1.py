#!/usr/bin/env python3
"""Fresh Linux build, unchanged finite qualification, and18 untimed captures. New frontdoor is static-tested only."""
import argparse,ast,hashlib,json,os,pathlib,signal,subprocess,time,traceback
HERE=pathlib.Path(__file__).resolve().parent

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,x):
 tmp=p.with_suffix(p.suffix+'.tmp');tmp.write_text(json.dumps(x,indent=2)+'\n')
 with tmp.open('rb')as f:os.fsync(f.fileno())
 tmp.replace(p)
def verify(inputs):
 pins={'BUILD-INPUTS-DIAG-r1.json':'c996c92e52ac5387cd8067b83fa5cac0644be10accc402c12292938fc21e1c22','RUNTIME-INPUTS-DIAG-r1.json':'3f44bd98e24773077dec465f541a3b85815d06befa96b8de26c954e9328d6e87'}
 members={}
 for n,expected in pins.items():
  assert sha(inputs/n)==expected,n
  for name,v in json.loads((inputs/n).read_text())['files'].items():
   p=inputs/name;assert p.resolve().is_relative_to(inputs.resolve());assert p.stat().st_size==v['bytes']and sha(p)==v['sha256'],name
   if name in members:assert members[name]==v
   members[name]=v
 for name in members:
  if name.endswith('.py'):ast.parse((inputs/name).read_text(),filename=name)
 return dict(status='PASS_FROZEN_INPUT_BYTE_AND_PYTHON_AST_CHECK',files=len(members),manifests=pins,source_plan_sha256=sha(inputs/'source/SOURCE.json'),new_frontdoor_Linux_runtime='NOT_EXECUTED_BY_STATIC_CHECK')
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--inputs',type=pathlib.Path,default=HERE/'inputs');p.add_argument('--static-check',action='store_true');g=p.add_mutually_exclusive_group();g.add_argument('--git',type=pathlib.Path,help='Existing local repository containing exact rawB72; no fetch');g.add_argument('--source-archive',type=pathlib.Path,help='Exact original authentic gzipSHA pinned in sourceplan');p.add_argument('--output',type=pathlib.Path,help='New short nonexistent root, e.g. /tmp/k3diag-replay');p.add_argument('--core-port',type=int,default=46640);p.add_argument('--qual-port',type=int,default=46700);p.add_argument('--capture-port',type=int,default=46710);a=p.parse_args();inputs=a.inputs.resolve();proof=verify(inputs)
 if a.static_check:print(json.dumps(proof,indent=2));return
 if not a.output or not(a.git or a.source_archive):p.error('runtime requires --output and one of --git/--source-archive')
 assert os.name=='posix'and pathlib.Path('/proc').is_dir(),'Linux required'
 out=a.output.resolve();assert not out.exists()and not any(x.isspace()for x in str(out));assert len(os.fsencode(out/'s/q-DIAG'/('.s.PGSQL.'+str(a.qual_port+1))))<104
 for port in [a.core_port,a.core_port+30,a.qual_port,a.qual_port+1,a.capture_port]:assert 1024<=port<=65530
 assert len({a.core_port,a.core_port+30,a.qual_port,a.qual_port+1,a.capture_port})==5
 import resource
 resource.setrlimit(resource.RLIMIT_AS,(3000000000,3000000000))
 out.mkdir();state=dict(status='RUNNING_NEW_PORTABLE_REPLAY',started_ns=time.time_ns(),timing_samples=0,inputs=proof,commands=[],frontdoor_sha256=sha(pathlib.Path(__file__)))
 def terminate(signum,frame):raise KeyboardInterrupt('termination requested')
 signal.signal(signal.SIGTERM,terminate)
 env={k:v for k,v in os.environ.items()if not k.startswith('PG')and k not in {'CFLAGS','CPPFLAGS','LDFLAGS','CC','CXX','MAKEFLAGS','MFLAGS','LD_PRELOAD','LD_LIBRARY_PATH'}};env.update(LC_ALL='C',GIT_NO_LAZY_FETCH='1',GIT_ALLOW_PROTOCOL='')
 build=['python3','-B',str(inputs/'build-harness/build.py'),'--source-plan',str(inputs/'source/SOURCE.json'),'--output',str(out/'build-r1'),'--core-port',str(a.core_port),'--jobs','1']
 build+=['--git',str(a.git.resolve())]if a.git else['--source-archive',str(a.source_archive.resolve())]
 stages=[('build',build,10800),('qualification',['python3','-B',str(inputs/'qualification/qualify.py'),'--build',str(out/'build-r1'),'--output',str(out/'qualification-r1'),'--first-port',str(a.qual_port)],3600),('capture',['python3','-B',str(inputs/'capture.py'),'--build',str(out/'build-r1'),'--qualified',str(out/'qualification-r1'),'--output',str(out/'captures-r1'),'--port',str(a.capture_port)],1800)]
 child=None
 try:
  for name,command,timeout in stages:
   item=dict(stage=name,args=command,started_ns=time.time_ns());state['commands'].append(item);save(out/'portable-replay.json',state)
   with(out/(name+'-frontdoor.log')).open('xb')as log:
    child=subprocess.Popen(command,env=env,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True);item['pid']=child.pid;save(out/'portable-replay.json',state)
    try:item['returncode']=child.wait(timeout=timeout)
    except BaseException:
     if child.poll()is None:
      os.killpg(child.pid,signal.SIGTERM)
      try:child.wait(timeout=480)
      except subprocess.TimeoutExpired:os.killpg(child.pid,signal.SIGKILL);child.wait(timeout=15)
     raise
   item['finished_ns']=time.time_ns();assert item['returncode']==0,(name,'failed attempt preserved; no retry')
  expected=[('build-r1','PASS_INSTRUMENTED_K3_BUILD_CORE239_POSTINGLIST'),('qualification-r1','PASS_DIAGNOSTIC_ORDINARY_SQL_NATIVE_BUDGET_FALLBACK'),('captures-r1','PASS_EIGHTEEN_UNTIMED_DISPATCH_CAPTURES')]
  for folder,status in expected:
   value=json.loads((out/folder/'status.json').read_text());assert value['status']==status and value['timing_samples']==0
   if folder!='build-r1':assert value['cleanup_errors']==[]and value['remaining_owned']==0
  verify(inputs);state.update(status='PASS_NEW_PORTABLE_BUILD_QUALIFICATION_EIGHTEEN_CAPTURES',finished_ns=time.time_ns(),status_receipts={folder:sha(out/folder/'status.json')for folder,status in expected})
 except BaseException as exc:state.update(status='FAILED_PRESERVED_NO_RETRY',error=repr(exc),traceback=traceback.format_exc());raise
 finally:save(out/'portable-replay.json',state)
 print(json.dumps(state,indent=2))
if __name__=='__main__':main()
