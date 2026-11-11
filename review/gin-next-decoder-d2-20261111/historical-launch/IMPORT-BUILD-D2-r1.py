#!/usr/bin/env python3
"""Parent-reviewed import and build-only launch, into one new owned VM158 namespace."""
import argparse,hashlib,json,os,pathlib,resource,subprocess,tarfile,time
ROOT=pathlib.Path('/home/reshke/allfuzz/gin-dec-d2-20261111')
ARCHIVE_SHA='e58471a6763421c5a7e52c829f68cd7e3ec2ffac7269050460322ed4cc045cff'
MANIFEST_SHA='11b348197ca1e912cd3616bb332a09a2780d70061e43c777aea15d25f75b30f7'
BASELINE_SHA='8c074fcf94a17d381e2df4a2b0554b925d76a777acb7e2f8a508abe7dfd2bbc4'

def sha(p):return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--archive',type=pathlib.Path,required=True);p.add_argument('--source-archive',type=pathlib.Path,required=True);p.add_argument('--root',type=pathlib.Path,default=ROOT);a=p.parse_args();root=a.root.resolve();assert root==ROOT
 assert sha(a.archive)==ARCHIVE_SHA and sha(a.source_archive)==BASELINE_SHA
 assert not(root/'inputs').exists()and not(root/'build-r1').exists()and not(root/'BUILD-LAUNCH-D2-r1.json').exists()
 root.mkdir(exist_ok=True);inputs=root/'inputs';inputs.mkdir(mode=0o700)
 with tarfile.open(a.archive)as stream:
  members=stream.getmembers();assert len(members)==16;names=[m.name for m in members];assert len(set(names))==16
  body=stream.extractfile('BUILD-INPUTS-D2-r1.json').read();assert hashlib.sha256(body).hexdigest()==MANIFEST_SHA
  manifest=json.loads(body);assert set(names)==set(manifest['files'])|{'BUILD-INPUTS-D2-r1.json'}
  for m in members:
   n=pathlib.PurePosixPath(m.name);assert not n.is_absolute()and'..'not in n.parts and m.isfile()and not m.mode&0o7000
   dest=inputs/n;dest.parent.mkdir(parents=True,exist_ok=True)
   with dest.open('xb')as out:out.write(stream.extractfile(m).read())
 for n,expected in manifest['files'].items():assert(inputs/n).stat().st_size==expected['bytes']and sha(inputs/n)==expected['sha256']
 command=['python3','-B',str(inputs/'build-harness/build.py'),'--source-archive',str(a.source_archive.resolve()),'--source-plan',str(inputs/'build-source/SOURCE.json'),'--output',str(root/'build-r1'),'--core-port','46900']
 environment={k:v for k,v in os.environ.items()if not k.startswith('PG')and k not in {'CFLAGS','CPPFLAGS','LDFLAGS','CC','CXX','MAKEFLAGS','MFLAGS','LD_PRELOAD','LD_LIBRARY_PATH'}};environment['LC_ALL']='C'
 resource.setrlimit(resource.RLIMIT_AS,(3000000000,3000000000))
 def nice():
  current=os.getpriority(os.PRIO_PROCESS,0)
  if current<10:os.nice(10-current)
 with(root/'build-launch-r1.log').open('xb')as log:child=subprocess.Popen(command,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,env=environment,start_new_session=True,preexec_fn=nice)
 receipt=dict(status='PARENT_REVIEWED_FOUR_MATCHED_BUILD_ONLY_STARTED',pid=child.pid,started_ns=time.time_ns(),command=command,archive_sha256=ARCHIVE_SHA,manifest_sha256=MANIFEST_SHA,source_plan_sha256=sha(inputs/'build-source/SOURCE.json'),baseline_archive_sha256=BASELINE_SHA,nice=10,jobs=2,child_RLIMIT_AS=3000000000,host_load=list(os.getloadavg()),qualification='NOT_STARTED',timing_samples=0)
 (root/'BUILD-LAUNCH-D2-r1.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt,indent=2))
if __name__=='__main__':main()
