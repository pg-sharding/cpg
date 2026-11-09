#!/usr/bin/env python3
"""Frozen fresh matched B72/V6/V7 release + V7 assert builds, nice10/j2."""
import hashlib,json,os,pathlib,shutil,subprocess,tarfile,time,traceback
R=pathlib.Path('/home/reshke/allfuzz/typed-leaf-v7-sql-20261108-r1')
I=R/'inputs';S=R/'common-source';B=R/'common-build';P=R/'prefix'
F='src/backend/access/nbtree/nbtsearch.c'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,d):
 p.write_text(json.dumps(d,indent=2)+'\n')
 with p.open('rb') as f:os.fsync(f.fileno())
def inv(r):
 return {str(p.relative_to(r)):{'bytes':p.stat().st_size,'sha256':sha(p)} for p in sorted(r.rglob('*')) if p.is_file() and not p.is_symlink()}
state={'status':'RUNNING','pid':os.getpid(),'start_ns':time.time_ns(),'commands':[],'nice':10,'jobs':2,'accepted_samples':0}
def run(a,name,cwd=B):
 state['phase']=name;save(R/'build-status.json',state)
 with (R/'build-proof'/f'{name}.log').open('w') as f:
  t=time.time_ns();q=subprocess.run(list(map(str,a)),cwd=cwd,stdout=f,stderr=subprocess.STDOUT,timeout=1800)
 rec={'name':name,'args':list(map(str,a)),'cwd':str(cwd),'start_ns':t,'end_ns':time.time_ns(),'rc':q.returncode,'log_sha256':sha(R/'build-proof'/f'{name}.log')}
 state['commands'].append(rec);save(R/'build-status.json',state)
 if q.returncode:raise RuntimeError(rec)
def capture(a):return subprocess.check_output(list(map(str,a)),text=True,stderr=subprocess.STDOUT)
try:
 os.nice(10);os.umask(0o077);(R/'build-proof').mkdir();S.mkdir();B.mkdir()
 inputs=json.loads((I/'inputs-manifest.json').read_text())
 assert all(sha(I/n)==m['sha256'] for n,m in inputs.items())
 archive=pathlib.Path('/home/reshke/allfuzz/hash-noop-sql-20261108-r1/inputs/base72.tar.gz')
 assert sha(archive)=='32a396e875b17122dc05dad59ecd11a3cb5a78f5b229bb5ce11fb769feaddb64'
 with tarfile.open(archive) as t:t.extractall(S,filter='data')
 expected=json.loads((I/'base-archive-manifest.json').read_text())['files'];assert len(expected)==7726 and inv(S)==expected
 sources={'base':(S/F).read_bytes(),'v6':(I/'v6-nbtsearch.c').read_bytes(),'v7':(I/'v7-nbtsearch.c').read_bytes()}
 for v,data in sources.items():
  dest=R/f'source-{v}';shutil.copytree(S,dest);(dest/F).write_bytes(data)
  actual=inv(dest);diffs=[n for n in actual if actual[n]!=expected[n]]
  assert diffs==([] if v=='base' else [F]),diffs
  save(R/'build-proof'/f'source-{v}-7726.json',actual)
 save(R/'BUILD-FREEZE.json',{'created_ns':time.time_ns(),'archive_sha256':sha(archive),'base_revision':'72b9498df9a369e747f8d96efb5a6cd33c2451e2','source_sha256':{v:hashlib.sha256(s).hexdigest() for v,s in sources.items()},'inputs':inputs,'controller_sha256':sha(R/'build.py'),'compiler':capture(['cc','--version']),'prefix':str(P),'common_source':str(S),'common_build':str(B),'flags':'-O2 -g','variants':['base','v6','v7','v7assert'],'core_each':239})
 for idx,v in enumerate(['base','v6','v7','v7assert']):
  if idx:
   shutil.rmtree(B);B.mkdir()
  (S/F).write_bytes(sources['v7' if v=='v7assert' else v])
  assert inv(S)==json.loads((R/'build-proof'/f'source-{"v7" if v=="v7assert" else v}-7726.json').read_text())
  config=[S/'configure','--prefix='+str(P),'--without-icu','--without-readline','--with-openssl',('--enable-cassert' if v=='v7assert' else '--disable-cassert'),'CFLAGS=-O2 -g']
  run(config,v+'-configure');run(['make','-j2'],v+'-build')
  dest=R/f'stage-{v}';run(['make','DESTDIR='+str(dest),'install'],v+'-install')
  for ext in ['amcheck','pageinspect']:
   run(['make','-C','contrib/'+ext,'-j2'],v+'-'+ext+'-build')
   run(['make','-C','contrib/'+ext,'DESTDIR='+str(dest),'install'],v+'-'+ext+'-install')
  stage=dest/pathlib.Path(str(P).lstrip('/'));out=R/'build-proof'/v;out.mkdir()
  headers={}
  for parent in [S/'src/include',B/'src/include',stage/'include']:
   headers[str(parent)]=inv(parent)
  save(out/'headers.json',headers)
  for name in ['nbtsearch','nbtutils','nbtinsert']:
   obj=B/'src/backend/access/nbtree'/f'{name}.o';shutil.copy2(obj,out/obj.name)
   (out/f'{name}.asm.txt').write_text(capture(['objdump','-drw',obj]))
   (out/f'{name}.symbols.txt').write_text(capture(['nm','-S',obj]))
  (out/'postgres.symbols.txt').write_text(capture(['nm','-S',stage/'bin/postgres']))
  (out/'postgres-bt-first.asm.txt').write_text(capture(['objdump','-d','--disassemble=_bt_first',stage/'bin/postgres']))
  if v=='v7':
   asm=(out/'nbtsearch.asm.txt').read_text();first=asm.split('<_bt_first>:',1)[1].split('\n\n',1)[0]
   assert '_bt_binsrch_read' in first and '_bt_search_int8' not in (out/'nbtsearch.symbols.txt').read_text()
  save(out/'binding.json',{'variant':v,'source_7726_sha256':sha(R/'build-proof'/f'source-{"v7" if v=="v7assert" else v}-7726.json'),'nbtsearch_source_sha256':sha(S/F),'installed_files':inv(stage),'compiler':capture(['cc','--version']),'configure':capture([stage/'bin/pg_config','--configure']),'cflags':capture([stage/'bin/pg_config','--cflags']),'ldflags':capture([stage/'bin/pg_config','--ldflags']),'headers_inventory_sha256':sha(out/'headers.json'),'postgres_notes':capture(['readelf','-n',stage/'bin/postgres']),'actual_nbtsearch_compile':[l for l in (R/'build-proof'/f'{v}-build.log').read_text().splitlines() if '-c ' in l and 'nbtsearch.c' in l]})
  run(['make','-C','src/test/regress','check','MAX_CONNECTIONS=2',f'EXTRA_REGRESS_OPTS=--port={13420+idx}'],v+'-core239')
  assert 'All 239 tests passed.' in (R/'build-proof'/f'{v}-core239.log').read_text()
  assert inv(S)==json.loads((R/'build-proof'/f'source-{"v7" if v=="v7assert" else v}-7726.json').read_text())
 state.update(status='PASS_MATCHED4_BUILD_CORE239',phase='COMPLETE',end_ns=time.time_ns(),source_freeze_sha256=sha(R/'BUILD-FREEZE.json'))
except BaseException as e:
 state.update(status='FAIL',exception=repr(e),end_ns=time.time_ns());(R/'build-exception.txt').write_text(traceback.format_exc());raise
finally:save(R/'build-status.json',state)
