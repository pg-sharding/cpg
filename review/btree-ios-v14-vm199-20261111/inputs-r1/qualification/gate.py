#!/usr/bin/env python3
"""Finite untimed IOS qualification on private copies; source bytes unchanged."""
from pathlib import Path
import argparse,datetime,hashlib,json,os,re,shlex,shutil,subprocess,sys,time,traceback
sys.path.insert(0,str(Path(__file__).resolve().parent.parent/'build-harness'))
import common
HERE=Path(__file__).resolve().parent
sha=common.sha
progress={}
w=None
target_seed=None
port=None

def run(cmd, log, cwd=None, env=None, expected=0):
    assert expected==0
    record=common.run(cmd,log,cwd=cwd or w,environment=env)
    progress.setdefault('commands',[]).append(record)
    common.save(w/'status.json',progress)
    return log.read_text()

def check_mode(mode, prefix, micro, result, logs):
    contract_count = 640 if mode in ('V13','V14','V14_assert') else 0
    old_data = target_seed
    data = w / ('data-' + mode)
    env = common.env(prefix)
    assert old_data.is_dir() and not old_data.is_symlink() and not (old_data / 'postmaster.pid').exists()
    assert subprocess.run([str(prefix / 'bin/pg_ctl'), '-D', str(old_data), 'status'], env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode == 3
    assert not data.exists()
    old_control = sha(old_data / 'global/pg_control')
    shutil.copytree(old_data, data)
    assert sha(old_data / 'global/pg_control') == old_control
    with (data / 'postgresql.conf').open('a') as f:
        f.write("\nlisten_addresses = ''\nunix_socket_directories = '" + str(w) + "'\nport = " + str(port) + "\n")
    conn = [str(prefix / 'bin/psql'), '-X', '-v', 'ON_ERROR_STOP=1', '-h', str(w), '-p', str(port), '-d', 'postgres']
    try:
        run([str(prefix / 'bin/pg_ctl'), '-D', str(data), '-l', str(logs / 'postmaster.txt'), '-w', 'start'], logs / 'start.txt', env=env)
        actual = run(conn + ['-A', '-t', '-c', 'SHOW debug_assertions;'], result / 'actual-mode.txt', env=env).strip()
        assert actual == ('on' if mode == 'V14_assert' else 'off'), (mode, actual)
        for name, reference in (('correctness.sql', 'correctness-base.txt'), ('correctness-boundaries.sql', 'boundaries-base.txt'), ('correctness-transition.sql', 'transition-base.txt')):
            output = result / reference
            run(conn + ['-f', str(w / 'inputs' / name)], output, env=env)
            assert output.read_bytes() == (w / 'inputs' / reference).read_bytes(), (mode, name, 'baseline output differs')
        sql = (
            "CREATE OR REPLACE FUNCTION ios_dispatch_oracle() RETURNS bigint AS '" + str(micro / 'ios_dispatch.so') + "', 'ios_dispatch_oracle' LANGUAGE C STRICT;\n"
            "CREATE OR REPLACE FUNCTION ios_pagecache_oracle() RETURNS bigint AS '" + str(micro / 'ios_dispatch.so') + "', 'ios_pagecache_oracle' LANGUAGE C STRICT;\n"
            "CREATE OR REPLACE FUNCTION ios_slot_micro(integer,bigint,integer,boolean,boolean,boolean) RETURNS bigint AS '" + str(micro / 'ios_slot.so') + "', 'ios_slot_micro' LANGUAGE C STRICT;\n"
            "SELECT 'oracle',ios_dispatch_oracle();\nSELECT 'contract',ios_pagecache_oracle();\n"
            "SELECT 'slot2r2',ios_slot_micro(2,128,2,true,false,false);\n"
            "SELECT 'slot2r64',ios_slot_micro(2,128,64,true,false,false);\n"
            "SELECT 'slot8',ios_slot_micro(8,128,64,true,true,false);\n"
            "SELECT 'slot32null',ios_slot_micro(32,128,64,true,true,true);\n"
        )
        script = result / 'native.sql'
        script.write_text(sql)
        output = run(conn + ['-q', '-A', '-t', '-f', str(script)], result / 'native-output.txt', env=env)
        assert output.splitlines() == ['oracle|751812', 'contract|' + str(contract_count), 'slot2r2|5504', 'slot2r64|5504', 'slot8|4096', 'slot32null|128']
        if mode in ('V13','V14','V14_assert'):
            ownership_sql = "CREATE OR REPLACE FUNCTION ios_v12_ownership_oracle() RETURNS text AS '" + str(micro / 'ownership.so') + "','ios_v12_ownership_oracle' LANGUAGE C STRICT; SELECT ios_v12_ownership_oracle();"
            answer = run(conn + ['-q', '-A', '-t', '-c', ownership_sql], result / 'ownership-answer.txt', env=env)
            ownership = json.loads(answer.strip())
            assert ownership == {'status':'PASS','checks':6941,'positive':120,'materialized':60,'custom':40,'fullhelper':40,'heappriority':5,'names':8,'custom_clears':45}
    finally:
        owned_pid = None
        if (data / 'postmaster.pid').exists():
            lines=(data/'postmaster.pid').read_text().splitlines()
            assert Path(lines[1]).resolve()==data.resolve()
            owned_pid=int(lines[0])
            pp=Path('/proc')/str(owned_pid)
            if pp.exists():assert os.fsencode(str(data))in(pp/'cmdline').read_bytes().split(b'\0')
            q=subprocess.run([str(prefix/'bin/pg_ctl'),'-D',str(data),'-m','fast','-w','stop'],env=env,capture_output=True,text=True,timeout=60)
            (logs/'stop.txt').write_text(q.stdout+q.stderr)
            assert q.returncode==0
            for _ in range(100):
                if not pp.exists():break
                time.sleep(.1)
            assert not pp.exists()
    q = subprocess.run([str(prefix / 'bin/pg_ctl'), '-D', str(data), 'status'], env=env, capture_output=True, text=True)
    assert q.returncode == 3 and not (data / 'postmaster.pid').exists()
    return {'status': 'PASS', 'actual_debug_assertions': actual, 'owned_stopped': True, 'pid_absent': True,
            'oracle': 751812, 'contract': contract_count, 'slot_checksums': [5504, 5504, 4096, 128],
            'target_outputs_equal_unchanged_base': True, 'old_control_unchanged': sha(old_data / 'global/pg_control') == old_control}


def main():
    global w,target_seed,port,progress
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--build',type=Path,required=True)
    p.add_argument('--correctness-seed',type=Path,required=True,help='Stopped historical baseline seed; copied read-only only')
    p.add_argument('--output',type=Path,required=True,help='New nonexistent qualification root with short Unix-socket path')
    p.add_argument('--port',type=int,default=40649)
    a=p.parse_args()
    assert not a.output.exists()
    w=a.output.resolve();w.mkdir();common.nice10()
    port=a.port;target_seed=a.correctness_seed.resolve()
    assert len(os.fsencode(w/('.s.PGSQL.'+str(port))))<104
    assert 1024<=port<=65535 and not target_seed.is_symlink()
    progress=dict(status='RUNNING_FINITE_IOS_QUALIFICATION',pid=os.getpid(),started_ns=time.time_ns(),timing_samples=0,roles={},commands=[])
    common.save(w/'status.json',progress)
    seed_before=None;build=None
    try:
        inputs=json.loads((HERE/'INPUTS.json').read_text())['files']
        for name,v in inputs.items():
            q=HERE/name
            assert q.stat().st_size==v['bytes'] and sha(q)==v['sha256'],name
        build=common.checked_build(a.build)
        base=Path(build['variants']['B']['prefix'])
        assert target_seed.is_dir() and not(target_seed/'postmaster.pid').exists()
        common.stopped(base,target_seed)
        seed_before=common.inventory(target_seed)
        common.save(w/'seed-before.json',seed_before)
        shutil.copytree(HERE/'inputs',w/'inputs')
        source=Path(build['common_source'])
        pinned=json.loads((Path(build['source_plan_path']).parent/'base-source-files.json').read_text())
        assert sha(source/'src/backend/access/nbtree/nbtsearch.c')==pinned['src/backend/access/nbtree/nbtsearch.c']['sha256']
        for role in ('B','V13','V14','V14_assert'):
            md=build['variants'][role];prefix=Path(md['prefix'])
            micro=w/('micro-'+role);result=w/('results-'+role);logs=w/('logs-'+role)
            for folder in (micro,result,logs):folder.mkdir()
            body=micro/'body';body.mkdir()
            run(['python3',HERE/'micro/extract-body.py',source,body/'returnitem-body.h',body/'extraction.json'],logs/'extract-body.txt')
            inc=prefix/'include/postgresql/server'
            flags=[] if role=='B' else ['-DMICRO_WITH_CACHE','-DMICRO_PAGE_CACHE','-DMICRO_CACHED_NATTS']
            pg=prefix/'bin/pg_config'
            compiler=[*shlex.split(common.capture([pg,'--cc'],prefix)),'-fPIC','-shared',*shlex.split(common.capture([pg,'--cflags'],prefix)),*shlex.split(common.capture([pg,'--cppflags'],prefix)),'-I'+str(inc),'-I'+str(prefix/'include/postgresql/internal')]
            run(compiler+flags+['-I'+str(body),HERE/'micro/dispatch_micro.c','-o',micro/'ios_dispatch.so'],logs/'compile-dispatch.txt',env=common.env(prefix))
            run(compiler+flags+[HERE/'micro/ios_slot_micro_counter.c','-o',micro/'ios_slot.so'],logs/'compile-slot.txt',env=common.env(prefix))
            if role!='B':run(compiler+[HERE/'ownership_oracle.c','-o',micro/'ownership.so'],logs/'compile-ownership.txt',env=common.env(prefix))
            for symbol,label in [('heapam_index_getnext_slot','backend-helper'),('heapam_index_only_tuple_getnext_slot','production-ios-callback')]+([] if role=='B' else [('tableam_index_fill_ios_cached_slot','production-outlined-helper')]):
                run(['objdump','-drwC','--disassemble='+symbol,prefix/'bin/postgres'],result/(label+'.asm.txt'))
            run(['objdump','-d','--disassemble=micro_fill',micro/'ios_slot.so'],result/'slot-helper.asm.txt')
            target=check_mode(role,prefix,micro,result,logs)
            expr=['sizeof(BTScanOpaqueData)','sizeof(BTScanPosItem)','sizeof(IndexScanDescData)','(long)&((BTScanOpaqueData*)0)->currPos']
            want=[27352,10,184,88] if role=='B' else [27384,10,192,120,32,16,24,12]
            if role!='B':expr+=['sizeof(IndexTupleDeformCache)','(long)&((IndexTupleDeformCache*)0)->values','(long)&((IndexTupleDeformCache*)0)->isnull','(long)&((IndexTupleDeformCache*)0)->natts']
            layouts={}
            for label,binary in [('backend',prefix/'bin/postgres'),('module',micro/'ios_dispatch.so')]:
                command=['gdb','--batch','-nx',binary]
                for e in expr:command+=['-ex','p /d '+e]
                text=run(command,result/('layout-'+label+'.txt'))
                vals=[int(x) for x in re.findall(r'^\$\d+ = (-?\d+)',text,re.M)]
                assert vals==want,(role,label,vals,want)
                layouts[label]=dict(zip(expr,vals))
            proof=dict(status='PASS',targeted=target,actual_layouts=layouts,build_postgres_sha256=md['postgres_sha256'],source_manifest_sha256=md['source_manifest_sha256'],module_sha256={q.name:sha(q) for q in micro.glob('*.so')},compiler=compiler)
            if role!='B':proof['expanded_ownership']=json.loads((result/'ownership-answer.txt').read_text())
            common.save(result/'proof.json',proof);progress['roles'][role]=proof
            assert common.inventory(target_seed)==seed_before
            common.checked_build(a.build)
            common.save(w/'status.json',progress)
        progress.update(status='PASS_FOUR_IOS_FINITE_GATES',finished_ns=time.time_ns(),build_receipt_sha256=sha(a.build/'build-receipt.json'),qualification_inputs_sha256=sha(HERE/'INPUTS.json'),counts={'roles':4,'target_outputs':12,'native_dispatch_checks_each':751812,'native_dispatch_checks_total':3007248,'cache_contracts_candidate_each':640,'cache_contracts_total':1920,'ownership_checks_candidate_each':6941,'ownership_checks_total':20823},scope='Original three SQL output comparisons + actual matching headers/callback/dispatch/cache/slot ownership. No performance or general concurrency proof.',cleanup={'own_clusters_stopped':True,'seed_unchanged':True,'matched_installs_unchanged':True},timing_samples=0)
    except BaseException as exc:
        progress.update(status='FAILED_PRESERVED',error=repr(exc),traceback=traceback.format_exc())
        raise
    finally:
        cleanup_errors=[]
        for role in ('B','V13','V14','V14_assert'):
            data=w/('data-'+role)
            if data.exists() and build is not None:
                try:
                    prefix=Path(build['variants'][role]['prefix'])
                    if (data/'postmaster.pid').exists():
                        lines=(data/'postmaster.pid').read_text().splitlines();assert Path(lines[1]).resolve()==data.resolve()
                        pid=int(lines[0]);proc=Path('/proc')/str(pid)
                        if proc.exists():assert os.fsencode(str(data)) in (proc/'cmdline').read_bytes().split(b'\0')
                        common.run([prefix/'bin/pg_ctl','-D',data,'-m','fast','-w','stop'],w/('finally-'+role+'.log'),prefix=prefix,timeout=60)
                    common.stopped(prefix,data);common.sync(data)
                except BaseException as exc:cleanup_errors.append(dict(role=role,error=repr(exc)))
        if seed_before is not None:
            try:
                assert common.inventory(target_seed)==seed_before
                common.stopped(Path(build['variants']['B']['prefix']),target_seed)
                common.checked_build(a.build)
            except BaseException as exc:cleanup_errors.append(dict(protected=str(target_seed),error=repr(exc)))
        progress['finally_cleanup_errors']=cleanup_errors
        if cleanup_errors:progress['status']='FAILED_CLEANUP'
        common.save(w/'status.json',progress)
        if cleanup_errors and not sys.exc_info()[0]:raise RuntimeError(cleanup_errors)

if __name__=='__main__':main()
