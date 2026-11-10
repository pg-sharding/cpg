#!/usr/bin/env python3
"""Separate finite CREATE INDEX comparison; never mix with scan samples."""
import argparse
import hashlib
import importlib.util
import itertools
import json
import os
import pathlib
import shutil
import statistics
import sys
import time
import traceback

ROOT = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'harness'))
from session import Session
from protocol import plan
spec = importlib.util.spec_from_file_location('bc', ROOT / 'build-harness/common.py')
bc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bc)


def spread(values):
    m = statistics.median(values)
    return dict(n=len(values), min=min(values), median=m, max=max(values),
                mean=statistics.mean(values), stdev=statistics.stdev(values),
                MAD=statistics.median(abs(x-m) for x in values), values=values)


def digest(value):
    return dict(rows=len(value.splitlines()), sha256=hashlib.sha256(value.encode()).hexdigest())


def nodes(node):
    yield node
    for child in node.get('Plans', []):
        yield from nodes(child)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--build', type=pathlib.Path, required=True)
    p.add_argument('--seed', type=pathlib.Path, required=True)
    p.add_argument('--output', type=pathlib.Path, required=True)
    p.add_argument('--first-port', type=int, default=45000)
    a = p.parse_args()
    out = a.output.resolve(); out.mkdir()
    bc.nice10()
    assert {0, 4} <= os.sched_getaffinity(0)
    build = bc.checked_build(a.build)
    seed = a.seed.resolve(); original = bc.inventory(seed)
    assert original == json.loads((seed.parent / 'seed-manifest.json').read_text())
    bc.save(out / 'input-seed-manifest.json', original)
    bc.save(out / 'protocol.json', dict(roles=plan('screen')['roles'], cohorts=2,
        rounds=14, warmups=2, retained=144, raw=168, parallel_maintenance_workers=0,
        maintenance_work_mem='128MB', rows=200002, fastupdate=False,
        timing='Only CREATE INDEX command CPU and client wall; DROP, checks and amcheck untimed. Warm cache, normal durability, no cache flush.'))
    bc.save(out / 'inputs.json', {str(x.relative_to(ROOT)): bc.sha(x) for x in [
        pathlib.Path(__file__), ROOT/'harness/session.py', ROOT/'harness/protocol.py', ROOT/'build-harness/common.py']})
    state = dict(status='RUNNING', clusters=[], started_ns=time.time_ns(), samples=0)
    owned = []; sessions = {}; rows = []
    bc.save(out / 'status.json', state)
    settings = "SET jit=off;SET max_parallel_maintenance_workers=0;SET maintenance_work_mem='128MB';SET statement_timeout='180s';SET lock_timeout='10s';"

    def save(): bc.save(out / 'status.json', state)

    def start(label, variant, data, cpu, port):
        prefix = pathlib.Path(build['variants'][variant]['prefix'])
        sock = bc.socket_directory(out/('s-'+label), port)
        item = dict(label=label, variant=variant, prefix=str(prefix), data=str(data), socket=str(sock), port=port)
        owned.append(item); state['clusters'].append(item); save()
        options = (f'-p {port} -k {sock} -c listen_addresses= -c shared_buffers=512MB '
                   '-c autovacuum=off -c jit=off -c max_parallel_workers=0 -c max_parallel_maintenance_workers=0 '
                   '-c max_connections=12 -c huge_pages=off -c timing_clock_source=system '
                   '-c checkpoint_timeout=1h -c max_wal_size=2GB')
        bc.run(['taskset','-c',cpu,prefix/'bin/pg_ctl','-D',data,'-l',out/(label+'-server.log'),'-o',options,'-w','start'],
               out/(label+'-start.log'),prefix=prefix,timeout=120)
        item['pid'] = int((data/'postmaster.pid').read_text().splitlines()[0])
        assert os.sched_getaffinity(item['pid']) == {cpu}
        assert bc.sha(pathlib.Path('/proc',str(item['pid']),'exe')) == build['variants'][variant]['postgres_sha256']
        s = Session(prefix,bc.local_dsn(sock,port),out/(label+'-stderr.txt'))
        sessions[label] = s; s.pid=int(s.sql('SELECT pg_backend_pid()'));item['backend_pid']=s.pid
        assert os.sched_getaffinity(s.pid) == {cpu}
        s.sql(settings); save()
        return item,s

    def stop(item):
        if item.get('stopped'): return
        s=sessions.pop(item['label'],None)
        if s: s.close(failed=state['status'].startswith('FAILED'))
        prefix=pathlib.Path(item['prefix']); data=pathlib.Path(item['data'])
        if (data/'postmaster.pid').exists():
            pid=int((data/'postmaster.pid').read_text().splitlines()[0])
            assert item.get('pid',pid)==pid
            assert bc.sha(pathlib.Path('/proc',str(pid),'exe'))==build['variants'][item['variant']]['postgres_sha256']
            bc.run([prefix/'bin/pg_ctl','-D',data,'-m','fast','-w','stop'],out/(item['label']+'-stop.log'),prefix=prefix,timeout=120)
        item['stop_proof']=bc.stopped(prefix,data)
        for key in ['pid','backend_pid']:
            if key in item:assert not pathlib.Path('/proc',str(item[key])).exists()
        assert not list(pathlib.Path(item['socket']).glob('.s.PGSQL.*'))
        item['stopped']=True;save()

    try:
        os.sched_setaffinity(0,{4})
        prepared=out/'seed';shutil.copytree(seed,prepared)
        assert bc.inventory(prepared)==original
        item,s=start('seed','B',prepared,0,a.first_port)
        s.sql('CREATE EXTENSION amcheck;DROP INDEX g1.docs_d_gin')
        queries=['common','common & rare0','dense2 & dense3']
        references={}
        s.sql('SET enable_bitmapscan=off;SET enable_indexscan=off;SET enable_indexonlyscan=off')
        for q,n in zip(queries,[200000,200,33333]):
            value=s.sql("SELECT id FROM g1.docs WHERE d @@ '"+q+"'::tsquery ORDER BY id")
            references[q]=digest(value);assert references[q]['rows']==n
        bc.save(out/'references.json',references)
        s.sql('CHECKPOINT');stop(item)
        prepared_manifest=bc.inventory(prepared);bc.save(out/'seed-manifest.json',prepared_manifest)
        roles=plan('screen')['roles'];orders=plan('screen')['orders']
        for cohort in [0,1]:
            cpu,client=(0,4) if cohort==0 else (4,0)
            os.sched_setaffinity(0,{client})
            state['cohort']=cohort;state['host_before_'+str(cohort)]=dict(load=list(os.getloadavg()),realtime_ns=time.time_ns());save()
            copies=[]
            for slot in range(6):
                data=out/f'data-c{cohort}-{slot}';shutil.copytree(prepared,data)
                assert bc.inventory(data)==prepared_manifest;bc.sync(data);copies.append(data)
            mapping=dict(zip(roles,range(6) if cohort==0 else reversed(range(6))))
            active={}
            try:
                for role in sorted(roles,key=mapping.get):
                    active[role]=start(f'c{cohort}-{role}',build['role_to_variant'][role],copies[mapping[role]],cpu,a.first_port+10+cohort*6+mapping[role])
                with (out/f'raw-c{cohort}.jsonl').open('x') as f:
                    for round_ in range(14):
                        order=orders[(round_ if round_<2 else round_-2)%6]
                        for position,role in enumerate(order):
                            item,s=active[role]
                            value=s.measured('CREATE INDEX bench_idx ON g1.docs USING gin(d) WITH(fastupdate=off)')
                            assert value['raw_result']==''
                            size=int(s.sql("SELECT pg_relation_size('g1.bench_idx')"));assert size>0
                            assert s.sql("SELECT gin_index_check('g1.bench_idx')") == ''
                            s.sql('SET enable_seqscan=off;SET enable_bitmapscan=on;SET enable_indexscan=off;SET enable_indexonlyscan=off')
                            for q in queries:
                                sql="SELECT id FROM g1.docs WHERE d @@ '"+q+"'::tsquery ORDER BY id"
                                assert digest(s.sql(sql))==references[q]
                                parsed=s.json('EXPLAIN(FORMAT JSON) '+sql)[0]['Plan']
                                assert any(n.get('Index Name')=='bench_idx' for n in nodes(parsed))
                            s.sql('DROP INDEX g1.bench_idx')
                            record=dict(cohort=cohort,round=round_,role=role,position=position,order=order,retained=round_>=2,
                                index_bytes=size,validation='amcheck + ordered Seq/GIN row digest and path PASS',observed=value)
                            f.write(json.dumps(record)+'\n');f.flush();rows.append(record);state['samples']=len(rows);save()
            finally:
                for item,s in reversed(list(active.values())):stop(item)
            state['host_after_'+str(cohort)]=dict(load=list(os.getloadavg()),realtime_ns=time.time_ns())
        assert len(rows)==168 and sum(x['retained'] for x in rows)==144
        absolute=[];pairs=[]
        for cohort in [0,1]:
            for metric in ['backend_cpu_ms','client_wall_ms']:
                def get(x):
                    v=x['observed'];return (v['command_delta']['cpu_ns'] if metric=='backend_cpu_ms' else v['client_ns'])/1e6
                points={(x['round'],x['role']):get(x) for x in rows if x['cohort']==cohort and x['retained']}
                for role in roles:absolute.append(dict(cohort=cohort,role=role,metric=metric,**spread([points[r,role] for r in range(2,14)])))
                for left,right in itertools.combinations(roles,2):
                    pairs.append(dict(cohort=cohort,left=left,right=right,metric=metric,
                        percent=spread([100*(points[r,right]/points[r,left]-1) for r in range(2,14)])))
        bc.save(out/'absolute.json',absolute);bc.save(out/'pairs.json',pairs)
        assert bc.inventory(seed)==original and bc.inventory(prepared)==prepared_manifest
        bc.checked_build(a.build)
        state.update(status='PASS',retained=144,warm=24,raw=168,finished_ns=time.time_ns())
    except BaseException as e:
        state.update(status='FAILED_PRESERVED',error=repr(e),traceback=traceback.format_exc());raise
    finally:
        errors=[]
        for item in reversed(owned):
            try:stop(item)
            except BaseException as e:errors.append(dict(label=item['label'],error=repr(e)))
        state['cleanup_errors']=errors
        if errors and state['status']=='PASS':state['status']='FAILED_CLEANUP'
        save()
        if errors and not sys.exc_info()[0]:raise RuntimeError(errors)


if __name__=='__main__':main()
