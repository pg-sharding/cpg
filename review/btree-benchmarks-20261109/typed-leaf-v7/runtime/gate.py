#!/usr/bin/env python3
"""Matched golden SQL, seqscan oracles, pinned-page helper oracle and standby."""
import gzip,hashlib,json,os,pathlib,subprocess,time,traceback
from session import R,W,STAGES,Session,sha,save,files,fsync_tree,check_builds,close_sessions,runtime_env,binary_env
I=R/'inputs';G=R/'gate-r5';owned=[];owned_pids=set();state={'status':'RUNNING','start_ns':time.time_ns(),'pid':os.getpid(),'checks':{}}
def run(a,log,timeout=240):
 with (G/log).open('w') as f:q=subprocess.run(list(map(str,a)),stdout=f,stderr=subprocess.STDOUT,timeout=timeout,env=binary_env(a[0]))
 if q.returncode:raise RuntimeError((a,q.returncode,log))
def phase(n):state['phase']=n;save(G/'status.json',state)
def runtime_inventory():
 actual=check_builds();sources={};stages={}
 inputs=json.loads((R/'BUILD-FREEZE.json').read_text())['inputs']
 assert all(sha(I/n)==m['sha256'] for n,m in inputs.items())
 assert sha(R/'build.py')==json.loads((R/'BUILD-FREEZE.json').read_text())['controller_sha256']
 for v in ['base','v6','v7']:
  sources[v]=files(R/f'source-{v}')
  assert len(sources[v])==7726 and sources[v]==json.loads((R/'build-proof'/f'source-{v}-7726.json').read_text())
 for v,p in STAGES.items():
  stages[v]=files(p)
  assert stages[v]==json.loads((R/'build-proof'/v/'binding.json').read_text())['installed_files']
 return {'elfs':actual,'source_inventories':sources,'stage_inventories':stages,'inputs':files(I)}
def start(v,data,port):
 p=STAGES[v];owned.append((v,data,port))
 run([p/'bin/pg_ctl','-D',data,'-o',f'-p{port} -k{R} -c listen_addresses= -c shared_buffers=128MB -c autovacuum=off -c max_wal_senders=5 -c wal_keep_size=128MB','-l',G/f'{data.name}-server.log','-w','start'],data.name+'-start.log')
 pid=int((data/'postmaster.pid').read_text().splitlines()[0]);owned_pids.add(pid)
 assert sha(pathlib.Path(f'/proc/{pid}/exe'))==check_builds()[v]
def stop(v,data,port):
 p=STAGES[v]
 initial=subprocess.run([str(p/'bin/pg_ctl'),'-D',str(data),'status'],capture_output=True,timeout=20,env=runtime_env(p))
 if initial.returncode!=3 or (data/'postmaster.pid').exists():
  pid=int((data/'postmaster.pid').read_text().splitlines()[0]);owned_pids.add(pid)
  assert sha(pathlib.Path(f'/proc/{pid}/exe'))==check_builds()[v]
  run([p/'bin/pg_ctl','-D',data,'-m','fast','-w','stop'],data.name+'-stop.log',timeout=90)
 q=subprocess.run([str(p/'bin/pg_ctl'),'-D',str(data),'status'],capture_output=True,timeout=20,env=runtime_env(p))
 assert q.returncode==3 and not (data/'postmaster.pid').exists()
 owned.remove((v,data,port));fsync_tree(data)
 return {'data':str(data),'port':port,'pg_ctl_status_rc':3,'pidfile_absent':True}
assert not G.exists(), 'New gate attempt only; existing output must be preserved'
G.mkdir()
try:
 os.nice(10);os.umask(0o077);baseline_inventory=runtime_inventory();save(G/'runtime-inputs-before.json',baseline_inventory)
 frozen={v:sha(p/'bin/postgres') for v,p in STAGES.items()};save(G/'runtime-before.json',frozen)
 # Each diagnostic module includes the complete actual frozen TU. Only static
 # helper calls are used; these modules are never loaded during SQL timing.
 modules={};template=(I/'leaf-shim-template-r3.c').read_text()
 template=template.replace('key->keysz = 1;', '_bt_metaversion(rel, &key->heapkeyspace, &key->allequalimage);\n\tkey->keysz = 1;')
 template=template.replace('key->scankeys->sk_flags &= ~SK_ISNULL;', '''key->scankeys->sk_flags &= ~SK_ISNULL;
 if (PG_NARGS() > 2)
 {
  int mode = PG_GETARG_INT32(2);
  if (mode == 1) fmgr_info(F_BTINT84CMP, &key->scankeys->sk_func);
  if (mode == 2) fmgr_info(F_BTINT82CMP, &key->scankeys->sk_func);
  if (mode == 3) { key->scankeys->sk_flags |= SK_ISNULL; key->anynullkeys = true; }
 }''')
 guard=(I/'v6-nbtsearch.c').read_text().split('int8search = ',1)[1].split(';',1)[0].replace('inskey.','key->')
 inc=STAGES['v7assert']/'include/postgresql/server';internal=STAGES['v7assert']/'include/postgresql/internal'
 for v in ['base','v6','v7']:
  source=R/f'source-{v}/src/backend/access/nbtree/nbtsearch.c';assert sha(source)==json.loads((R/'BUILD-FREEZE.json').read_text())['source_sha256'][v]
  call={'base':'_bt_binsrch(rel, key, buffer)','v6':'(use_typed ? _bt_binsrch_int8_read(rel, key, buffer) : _bt_binsrch(rel, key, buffer))','v7':'_bt_binsrch_read(rel, key, buffer)'}[v]
  wrapper=G/f'oracle-{v}.c';wrapper.write_text('#include "'+str(source)+'"\n'+template.replace('@NAME@','tleaf_probe_'+v).replace('@GUARD@',guard).replace('@CALL@',call))
  obj=G/f'oracle-{v}.o';mod=G/f'oracle-{v}.so'
  cmd=['cc','-O2','-g','-fPIC','-I'+str(inc),'-I'+str(internal),'-c',wrapper,'-o',obj]
  run(cmd,f'oracle-{v}-compile.log');run(['cc','-shared','-o',mod,obj],f'oracle-{v}-link.log')
  modules[v]={'path':str(mod),'sha256':sha(mod),'wrapper_sha256':sha(wrapper),'source_sha256':sha(source),'compile_args':list(map(str,cmd))}
 save(G/'oracle-module-bindings.json',modules)
 outputs={};proof={};assert_session=None
 for ix,v in enumerate(['base','v6','v7','v7assert']):
  phase('SQL_'+v);data=R/f'data-correct-r5-{v}';port=13430+ix;p=STAGES[v]
  run([p/'bin/initdb','-D',data,'--no-locale','--encoding=UTF8'],v+'-init.log');start(v,data,port);s=Session(port,variant=v)
  try:
   outputs[v]={}
   for name in ['targets.sql','correctness-null-pivots.sql','correctness-unique.sql','correctness-lifecycle-extra.sql']:
    answer=s.command('\\i '+str(I/name));(G/f'{v}-{name}.out').write_text(answer+'\n');outputs[v][name]=sha(G/f'{v}-{name}.out')
   # Save the complete ordered multiset of each table outside any interval;
   # verify against the immutable setup formula, independently of PostgreSQL.
   fullproof={};want=[(k,k*3) for k in range(-30000,30001)]+[(3,k) for k in range(1,60001)]+[(-9223372036854775808,1),(9223372036854775807,2),(None,3)]
   want.sort(key=lambda x:(x[0] is not None,x[0] or 0,x[1]))
   fixed='\n'.join(('' if k is None else str(k))+'|'+str(value) for k,value in want)
   for table in ['typed_perm','typed_unlogged','typed_temp','typed_desc','typed_include','typed_multi','typed_custom','typed_null_first']:
    actual=s.command(f'SELECT k,v FROM {table} ORDER BY k NULLS FIRST,v;');assert actual==fixed,(v,table)
    dest=G/f'{v}-{table}-complete.txt.gz'
    with dest.open('wb') as f:
     with gzip.GzipFile(filename='',mode='wb',fileobj=f,mtime=0) as z:z.write((actual+'\n').encode())
    fullproof[table]={'rows':len(want),'formula_match':True,'uncompressed_sha256':hashlib.sha256((actual+'\n').encode()).hexdigest(),'gzip_sha256':sha(dest)}
   proof[v+'_complete_multisets']=fullproof
   if v=='v7assert':
    for m in modules:
     s.command(f"CREATE FUNCTION tleaf_probe_{m}(regclass,bigint[]) RETURNS text AS '{modules[m]['path']}','tleaf_probe_{m}' LANGUAGE C STRICT;")
     s.command(f"CREATE FUNCTION tleaf_probe_{m}_mode(regclass,bigint[],integer) RETURNS text AS '{modules[m]['path']}','tleaf_probe_{m}' LANGUAGE C STRICT;")
    s.command('\\i '+str(I/'linear-fixture-r4.sql'))
    s.command('CREATE INDEX q_custom_idx ON q(k typed_custom_ops);')
    indices=['q_idx','q_desc_idx','q_include_idx','q_multi_idx','qd_idx','q_custom_idx','typed_perm_idx','typed_unlogged_idx','typed_temp_k_idx','typed_null_first_idx','sep_null_pivots_idx','leaf_empty_idx','typed_empty_idx']
    # PostgreSQL gives the explicitly created temp index the literal name.
    indices[8]='typed_temp_idx'
    array="ARRAY['-9223372036854775808',-30000,-20001,-20000,-1,0,2,3,4,19999,20000,20001,30000,'9223372036854775807']::bigint[]"
    oracle={m:{idx:s.command(f"SELECT tleaf_probe_{m}('{idx}',{array});") for idx in indices} for m in modules}
    assert oracle['base']==oracle['v6']==oracle['v7'],oracle
    assert all(int(oracle['v7'][idx].split(':')[2])>0 for idx in ['q_idx','typed_perm_idx','typed_unlogged_idx','typed_temp_idx','typed_null_first_idx','sep_null_pivots_idx','leaf_empty_idx'])
    assert all(int(oracle['v7'][idx].split(':')[2])==0 for idx in ['q_desc_idx','q_include_idx','q_multi_idx','qd_idx','q_custom_idx'])
    proof['locked_page_oracle']=oracle
    mode_oracle={m:{str(mode):s.command(f"SELECT tleaf_probe_{m}_mode('typed_perm_idx',ARRAY[-30000,-1,0,3,30000]::bigint[],{mode});") for mode in [1,2,3]} for m in modules}
    assert mode_oracle['base']==mode_oracle['v6']==mode_oracle['v7']
    assert all(int(value.split(':')[2])==0 for value in mode_oracle['v7'].values())
    proof['cross_int4_int2_null_argument_locked_page_fallback_oracle']=mode_oracle
    proof['synthetic_key_metapage_metadata']='After _bt_mkscankey(rel,NULL), every diagnostic wrapper initializes heapkeyspace and allequalimage with native _bt_metaversion on the same AccessShareLock relation, matching production _bt_first; no constants and no assertion disabled.'
    proof['actual_assert_backend']='The actual V7assert helper compares typed offset with generic on the same pinned/read-locked page on every selected helper call.'
    proof['pivot_shapes']=s.command("SELECT p.type,count(*) FILTER(WHERE i.htid IS NULL AND i.data<>''),count(*) FILTER(WHERE i.htid IS NOT NULL) FROM generate_series(1,pg_relation_size('typed_perm_idx')/8192-1)b CROSS JOIN LATERAL bt_page_stats('typed_perm_idx',b)p CROSS JOIN LATERAL bt_page_items('typed_perm_idx',b)i WHERE p.type IN('i','r') GROUP BY p.type ORDER BY p.type;")
    proof['null_pivot_shapes']=s.command("SELECT p.type,count(*) FILTER(WHERE i.nulls),count(*) FILTER(WHERE i.htid IS NULL) FROM generate_series(1,pg_relation_size('sep_null_pivots_idx')/8192-1)b CROSS JOIN LATERAL bt_page_stats('sep_null_pivots_idx',b)p CROSS JOIN LATERAL bt_page_items('sep_null_pivots_idx',b)i WHERE p.type IN('i','r') GROUP BY p.type ORDER BY p.type;")
    assert_session=s;s=None
  finally:
   if s:s.close()
  if v!='v7assert':proof[v+'_stop']=stop(v,data,port)
 for name in outputs['base']:
  assert len({outputs[v][name] for v in outputs})==1,(name,outputs)
 proof['all_four_outputs_byte_equal']=outputs
 phase('PHYSICAL_STANDBY');lsn=assert_session.command('SELECT pg_current_wal_insert_lsn();');assert_session.close();assert_session=None
 standby=R/'data-correct-r5-standby';run([STAGES['v7assert']/'bin/pg_basebackup','-h',R,'-p','13433','-D',standby,'-R','-X','stream','--checkpoint=fast'],'standby-basebackup.log');start('v7assert',standby,13434);s=Session(13434,variant='v7assert')
 try:
  for _ in range(100):
   if s.command(f"SELECT coalesce(pg_last_wal_replay_lsn()>='{lsn}'::pg_lsn,false);")=='t':break
   time.sleep(.1)
  else:raise RuntimeError('standby replay lag')
  recovery=s.command('\\i '+str(I/'recovery-targets.sql'));(G/'recovery-targets.out').write_text(recovery+'\n')
  assert 'recovery-targets:ok' in recovery and s.command('SELECT pg_is_in_recovery();')=='t'
  oracle=s.command("SELECT tleaf_probe_v7('typed_perm_idx',ARRAY[-30000,-1,0,3,30000]::bigint[]);");assert int(oracle.split(':')[2])>0
  proof['standby']={'recovery_targets_sha256':sha(G/'recovery-targets.out'),'same_locked_page_oracle':oracle,'pg_is_in_recovery':True,'replay_lsn_at_least':lsn}
 finally:s.close()
 proof['standby_stop']=stop('v7assert',standby,13434);proof['assert_primary_stop']=stop('v7assert',R/'data-correct-r5-v7assert',13433)
 assert {v:sha(p/'bin/postgres') for v,p in STAGES.items()}==frozen
 assert runtime_inventory()==baseline_inventory
 proof['runtime_elf_unchanged']=True
 proof['source_all_7726_stages_inputs_unchanged']=True
 proof['serializable_race']={'source_review':'B72 _bt_search, predicate lock and serializable retry are byte-restored; nbtree-first-empty injection exists behind USE_INJECTION_POINTS. These matched builds have injection points disabled. Single-session lifecycle smoke passed; two-session barrier was NOT RUN.','two_session_barrier':'NOT RUN'}
 proof['scope']='SQL answer aggregates and ordered multiset hashes independently compared with seqscan by copied typed_ref; B72 output fixed as golden. No expected regenerated from candidate. Standby and pinned-leaf diagnostic checks untimed.'
 save(G/'proof.json',proof);state.update(status='PASS_MATCHED_SQL_ORACLE_LIFECYCLE_STANDBY',end_ns=time.time_ns())
except BaseException as e:
 state.update(status='FAIL',exception=repr(e),end_ns=time.time_ns());(G/'exception.txt').write_text(traceback.format_exc());raise
finally:
 stops=[];cleanup_errors=[]
 if 'assert_session' in globals() and assert_session is not None:cleanup_errors+=close_sessions([assert_session])
 for v,data,port in list(reversed(owned)):
  try:stops.append(stop(v,data,port))
  except BaseException as e:cleanup_errors.append({'data':str(data),'error':repr(e)})
 state['finally_stops']=stops;state['remaining_owned']=len(owned);state['cleanup_errors']=cleanup_errors;state['owned_postmaster_pids']=sorted(owned_pids);state['owned_postmaster_pids_absent']=all(not pathlib.Path(f'/proc/{pid}').exists() for pid in owned_pids)
 if cleanup_errors or owned or not state['owned_postmaster_pids_absent']:
  failed_before=state['status']=='FAIL';state['status']='FAIL_CLEANUP';save(G/'status.json',state)
  if not failed_before:raise RuntimeError('gate cleanup incomplete')
 else:save(G/'status.json',state)
 fsync_tree(G)
