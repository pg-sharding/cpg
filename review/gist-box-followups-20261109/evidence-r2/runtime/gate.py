#!/usr/bin/env python3
"""Fresh fixture and finite full-backend equivalence before BOX timings."""
import gzip
import json
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import time
import traceback
from common import ROOT, HERE, BUILD, Runtime, sha, save, inventory, fsync_tree, env

out=ROOT/'gate-r1'
out.mkdir()
os.umask(0o077)
os.nice(max(0,10-os.getpriority(os.PRIO_PROCESS,0)))
runtime=Runtime(out)
state={'status':'RUNNING','accepted_samples':0,'started_ns':time.time_ns(),'checks':{}}
seed=ROOT/'canonical'
module=ROOT/'modules/box-am.so'
sqlcases=json.loads((HERE/'sql-cases.json').read_text())
microcases=json.loads((HERE/'micro-cases.json').read_text())
verify=json.loads((HERE/'verification-queries.json').read_text())
reset="SET enable_seqscan=on;SET enable_indexscan=on;SET enable_indexonlyscan=on;SET enable_bitmapscan=on;SET enable_material=on;SET work_mem='64MB';"

def store_answer(name, text):
    path=out/(name+'.txt.gz')
    data=(text+'\n').encode()
    with path.open('xb') as f:
        with gzip.GzipFile(filename='',mode='wb',fileobj=f,mtime=0) as stream:stream.write(data)
    return {'rows':len(text.splitlines()) if text else 0,'sha256':__import__('hashlib').sha256(data).hexdigest(),'gzip_sha256':sha(path),'file':path.name}

try:
    prefix=runtime.prefix('B')
    module.parent.mkdir()
    config=lambda name:subprocess.check_output([str(prefix/'bin/pg_config'),'--'+name],text=True).strip()
    flags=shlex.split(config('cflags'))+shlex.split(config('cppflags'))
    inc=prefix/'include/postgresql'
    runtime.run('B',['gcc',*flags,'-fPIC','-I'+str(inc/'server'),'-I'+str(inc/'internal'),'-c',HERE/'am-micro.c','-o',module.with_suffix('.o')],'module-compile.log')
    runtime.run('B',['gcc','-shared','-o',module,module.with_suffix('.o')],'module-link.log')
    state['module']={'path':str(module),'sha256':sha(module),'source_sha256':sha(HERE/'am-micro.c'),'flags':flags}
    runtime.run('B',[prefix/'bin/initdb','-D',seed,'--no-locale','--encoding=UTF8'],'seed-initdb.log')
    rec=runtime.start('B',seed,'seed')
    runtime.run('B',[prefix/'bin/psql','-X','-h',rec['socket'],'-p',str(rec['port']),'-d','postgres','-v','ON_ERROR_STOP=1','-v','module='+str(module),'-f',HERE/'setup.sql'],'seed-setup.log')
    s=runtime.open(rec)
    try:
        s.command(f"CREATE FUNCTION public.box_am_micro(regclass,box[],integer) RETURNS text AS '{module}','box_am_micro' LANGUAGE C STRICT;")
        assert s.command('SELECT count(*) FROM s2.boxes;')=='200000'
        expected={}
        for case in sqlcases:
            s.command(reset+case['settings'])
            expected[case['name']]=s.command(case['sql']+';')
        for case in microcases:
            expected[case['name']]=s.command(case['answer_sql']+';')
        refs={}
        s.command('SET enable_seqscan=on;SET enable_indexscan=off;SET enable_indexonlyscan=off;SET enable_bitmapscan=off;')
        for q in verify:
            text=s.command('SELECT * FROM ('+q['sql']+') reference ORDER BY 1;')
            refs[q['name']]=text
            state['checks'].setdefault('sequential_references',{})[q['name']]=store_answer('reference-'+q['name'],text)
        s.command('CHECKPOINT;')
    finally:s.close()
    state['seed_stop']=runtime.stop(rec)
    fsync_tree(seed)
    seed_manifest=inventory(seed)
    save(ROOT/'SEED.json',{'files':seed_manifest,'expected':expected,'module_sha256':sha(module),'created_ns':time.time_ns()})
    results={}
    for ix,role in enumerate(['B','R','C','D','C_assert','D_assert']):
        state['phase']=role
        save(out/'status.json',state)
        data=ROOT/('data-gate-'+role)
        shutil.copytree(seed,data)
        assert inventory(data)==seed_manifest
        rec=runtime.start(role,data,'g'+str(ix))
        s=runtime.open(rec)
        proof={'queries':{},'sql':{},'micro':{}}
        try:
            s.command('SET enable_seqscan=off;SET enable_bitmapscan=off;SET enable_indexscan=on;SET enable_indexonlyscan=on;')
            for q in verify:
                query='SELECT * FROM ('+q['sql']+') reference ORDER BY 1'
                text=s.command(query+';')
                assert text==refs[q['name']],(role,q['name'])
                proof['queries'][q['name']]=store_answer(role+'-'+q['name'],text)
            for case in sqlcases:
                s.command(reset+case['settings'])
                answer=s.command(case['sql']+';')
                assert answer==expected[case['name']],(role,case['name'],answer,expected[case['name']])
                proof['sql'][case['name']]={'answer':answer,'plan':json.loads(s.command('EXPLAIN(ANALYZE,BUFFERS,TIMING OFF,FORMAT JSON) '+case['sql']+';'))[0]}
            proof['prepared_rescans']=s.command('\\i '+str(HERE/'prepared-rescan.sql'))
            for case in microcases:
                got=json.loads(s.command(case['sql']+';'))
                assert got['tids']==int(expected[case['name']]) and got['scans']==case['scans'],(role,case,got)
                proof['micro'][case['name']]=got
            s.command(reset+'SET enable_seqscan=off;SET enable_indexscan=off;SET enable_indexonlyscan=off;SET work_mem=\'64kB\';')
            query='SELECT id FROM s2.boxes WHERE b && box(point(-1,-1),point(2000,2000)) ORDER BY id'
            bitmap=s.command(query+';')
            s.command(reset+'SET enable_indexscan=off;SET enable_indexonlyscan=off;SET enable_bitmapscan=off;')
            assert s.command(query+';')==bitmap
            proof['bitmap_full_multiset']=store_answer(role+'-bitmap',bitmap)
            s.command(reset+'SET enable_seqscan=off;SET enable_bitmapscan=off;')
            projected='SELECT b::text FROM s2.boxes WHERE b && box(point(100,100),point(105,105)) ORDER BY 1'
            index_projection=s.command(projected+';')
            s.command(reset+'SET enable_indexscan=off;SET enable_indexonlyscan=off;SET enable_bitmapscan=off;')
            assert s.command(projected+';')==index_projection
            proof['projection_full_multiset']=store_answer(role+'-projection',index_projection)
            s.command(reset+'SET enable_seqscan=off;SET enable_bitmapscan=off;')
            assert s.command('SELECT count(*) FROM s2.boxes;')=='200000'
            proof['zero_key_count']='200000'
            results[role]=proof
        finally:
            s.close()
            runtime.stop(rec)
    assert len({p['prepared_rescans'] for p in results.values()})==1
    state['results']=results
    assert inventory(seed)==seed_manifest and sha(module)==state['module']['sha256']
    assert runtime.receipt==__import__('common').builds()
    save(out/'proof.json',state)
    state['status']='PASS_COMPLETE_BACKENDS_FINITE_SQL_AM_EQUIVALENCE'
except BaseException as e:
    state.update(status='FAIL',error=repr(e),traceback=traceback.format_exc())
    raise
finally:
    state['cleanup']=runtime.cleanup()
    state['finished_ns']=time.time_ns()
    save(out/'status.json',state)
    assert not state['cleanup']['errors'] and not state['cleanup']['remaining_owned'] and state['cleanup']['pids_absent']
print(state['status'])
