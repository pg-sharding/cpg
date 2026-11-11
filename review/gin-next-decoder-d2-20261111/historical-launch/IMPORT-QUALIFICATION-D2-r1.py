#!/usr/bin/env python3
"""Import one reviewed valid-input overlay and queue qualification after its own build; no timings."""
import argparse,hashlib,json,os,pathlib,resource,subprocess,tarfile,time
ROOT=pathlib.Path('/home/reshke/allfuzz/gin-dec-d2-20261111')
ARCHIVE_SHA='d458fac88f248ccebce84ec3fcbfc52c00459446c74689e7d75b8da32e28646a'
MANIFEST_SHA='526681c089d361901c67d74a981c35674f45429d48cd864f806a432fe33a92fb'
BUILD_MANIFEST_SHA='11b348197ca1e912cd3616bb332a09a2780d70061e43c777aea15d25f75b30f7'
def sha(p):return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--archive',type=pathlib.Path,required=True);p.add_argument('--wait-build-pid',type=int,required=True);p.add_argument('--root',type=pathlib.Path,default=ROOT);a=p.parse_args();root=a.root.resolve();assert root==ROOT;inputs=root/'inputs'
 assert sha(a.archive)==ARCHIVE_SHA and sha(inputs/'BUILD-INPUTS-D2-r1.json')==BUILD_MANIFEST_SHA
 for n,v in json.loads((inputs/'BUILD-INPUTS-D2-r1.json').read_text())['files'].items():assert(inputs/n).stat().st_size==v['bytes']and sha(inputs/n)==v['sha256']
 launch=json.loads((root/'BUILD-LAUNCH-D2-r1.json').read_text());assert launch['pid']==a.wait_build_pid
 assert not(root/'qualification-r1').exists()and not(root/'qualification-chain-r1.json').exists()and not(root/'QUALIFICATION-LAUNCH-D2-r1.json').exists()
 with tarfile.open(a.archive)as stream:
  members=stream.getmembers();assert len(members)==12;names=[m.name for m in members];assert len(set(names))==12
  body=stream.extractfile('QUALIFICATION-INPUTS-D2-r1.json').read();assert hashlib.sha256(body).hexdigest()==MANIFEST_SHA;manifest=json.loads(body)
  assert manifest['build_manifest_sha256']==BUILD_MANIFEST_SHA and set(names)==set(manifest['files'])|{'QUALIFICATION-INPUTS-D2-r1.json'}
  for m in members:
   n=pathlib.PurePosixPath(m.name);assert not n.is_absolute()and'..'not in n.parts and m.isfile()and not m.mode&0o7000;dest=inputs/n;assert not dest.exists();dest.parent.mkdir(parents=True,exist_ok=True)
   with dest.open('xb')as out:out.write(stream.extractfile(m).read())
 for n,v in manifest['files'].items():assert(inputs/n).stat().st_size==v['bytes']and sha(inputs/n)==v['sha256']
 command=['python3','-B',str(inputs/'run-qualification-r1.py'),'--root',str(root),'--wait-build-pid',str(a.wait_build_pid),'--wait-seconds','3600'];environment={k:v for k,v in os.environ.items()if not k.startswith('PG')and k not in {'MAKEFLAGS','MFLAGS','CFLAGS','CPPFLAGS','LDFLAGS','CC','CXX','LD_PRELOAD','LD_LIBRARY_PATH'}};environment['LC_ALL']='C'
 resource.setrlimit(resource.RLIMIT_AS,(3000000000,3000000000))
 def nice():
  priority=os.getpriority(os.PRIO_PROCESS,0)
  if priority<10:os.nice(10-priority)
 with(root/'qualification-waitchain-launch-r1.log').open('xb')as log:child=subprocess.Popen(command,env=environment,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True,preexec_fn=nice)
 receipt=dict(status='PARENT_REVIEWED_VALID_QUALIFICATION_WAITCHAIN_STARTED',pid=child.pid,started_ns=time.time_ns(),wait_build_pid=a.wait_build_pid,command=command,archive_sha256=ARCHIVE_SHA,qualification_manifest_sha256=MANIFEST_SHA,source_plan_sha256=sha(inputs/'build-source/SOURCE.json'),nice=10,child_RLIMIT_AS=3000000000,timing_samples=0)
 (root/'QUALIFICATION-LAUNCH-D2-r1.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt,indent=2))
if __name__=='__main__':main()
