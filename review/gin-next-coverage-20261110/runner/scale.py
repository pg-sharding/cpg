#!/usr/bin/env python3
"""Larger static SQL fixture, with separate warm and restart-only scopes."""
import argparse
import importlib.util
import itertools
import json
import os
import pathlib
import shutil
import sys
import time
import traceback

ROOT = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'harness'))
from session import Session
from operations import bc, digest, host, nodes, spread

loader = importlib.util.spec_from_file_location('scale_protocol', ROOT / 'scale-protocol.py')
protocol = importlib.util.module_from_spec(loader)
loader.loader.exec_module(protocol)
SEQ = 'SET enable_seqscan=on;SET enable_bitmapscan=off;SET enable_indexscan=off;SET enable_indexonlyscan=off'
GIN = 'SET enable_seqscan=off;SET enable_bitmapscan=on;SET enable_indexscan=off;SET enable_indexonlyscan=off'
SETTINGS = ("SET jit=off;SET max_parallel_workers_per_gather=0;SET max_parallel_maintenance_workers=0;"
            "SET gin_fuzzy_search_limit=0;SET work_mem='64MB';SET maintenance_work_mem='128MB';"
            "SET statement_timeout='180s';SET lock_timeout='10s'")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--build', type=pathlib.Path, required=True)
    parser.add_argument('--qualified-from', type=pathlib.Path, required=True)
    parser.add_argument('--large-from', type=pathlib.Path, help='PASS warm-mode output; its stopped seed is read-only')
    parser.add_argument('--mode', choices=['warm', 'restart'], required=True)
    parser.add_argument('--output', type=pathlib.Path, required=True)
    parser.add_argument('--first-port', type=int, default=45740)
    args = parser.parse_args()
    spec = protocol.plan(args.mode)
    out = args.output.resolve()
    out.mkdir()
    bc.nice10()
    assert {0, 4} <= os.sched_getaffinity(0)
    build = bc.checked_build(args.build)
    source = pathlib.Path(build['common_source'])
    source_manifest = json.loads((args.build / 'C11_assert-source-inventory.json').read_text())
    assert bc.inventory(source) == source_manifest
    origin = args.qualified_from.resolve()
    proof = json.loads((origin / 'status.json').read_text())
    assert proof['status'] == 'PASS' and proof['mode'] == 'qualify' and not proof['cleanup_errors']
    build_sha = bc.sha(args.build / 'build-receipt.json')
    assert proof['build_receipt_sha256'] == build_sha
    original_seed = origin / 'seed'
    original_inventory = json.loads((origin / 'seed-manifest.json').read_text())
    assert bc.inventory(original_seed) == original_inventory
    bc.stopped(pathlib.Path(build['variants']['B']['prefix']), original_seed)
    frozen = {str(p.relative_to(ROOT)): dict(bytes=p.stat().st_size, sha256=bc.sha(p))
              for p in [ROOT / 'scale.py', ROOT / 'scale-protocol.py', ROOT / 'operations.py',
                        ROOT / 'protocol.py', ROOT / 'harness/session.py', ROOT / 'harness/common.py',
                        ROOT / 'build-harness/common.py']}
    bc.save(out / 'frozen-inputs.json', frozen)
    bc.save(out / 'protocol.json', spec)
    bc.save(out / 'provenance.json', dict(build=str(args.build.resolve()), build_receipt_sha256=build_sha,
            qualified_from=str(origin), qualification_status_sha256=bc.sha(origin / 'status.json')))
    state = dict(status='RUNNING', mode=args.mode, build_receipt_sha256=build_sha, clusters=[],
                 samples=0, host_before=host(), started_ns=time.time_ns())
    owned, sessions, samples = [], {}, []
    bc.save(out / 'status.json', state)

    def save(): bc.save(out / 'status.json', state)

    def start(label, variant, data, cpu, port):
        prefix = pathlib.Path(build['variants'][variant]['prefix'])
        sock = bc.socket_directory(out / ('s-' + label), port)
        item = dict(label=label, variant=variant, data=str(data), prefix=str(prefix), socket=str(sock), port=port)
        owned.append(item)
        state['clusters'].append(item)
        save()
        opts = (f'-p {port} -k {sock} -c listen_addresses= -c shared_buffers=64MB -c autovacuum=off '
                '-c jit=off -c max_parallel_workers=0 -c max_parallel_maintenance_workers=0 '
                '-c max_connections=8 -c huge_pages=off -c timing_clock_source=system '
                '-c checkpoint_timeout=1h -c max_wal_size=2GB')
        bc.run(['taskset', '-c', cpu, prefix / 'bin/pg_ctl', '-D', data, '-l', out / (label + '-server.log'),
                '-o', opts, '-w', 'start'], out / (label + '-start.log'), prefix=prefix, timeout=120)
        item['pid'] = int((data / 'postmaster.pid').read_text().splitlines()[0])
        assert os.sched_getaffinity(item['pid']) == {cpu}
        assert bc.sha(pathlib.Path('/proc', str(item['pid']), 'exe')) == build['variants'][variant]['postgres_sha256']
        s = Session(prefix, bc.local_dsn(sock, port), out / (label + '-stderr.txt'))
        sessions[label] = s
        s.pid = int(s.sql('SELECT pg_backend_pid()'))
        item['backend_pid'] = s.pid
        assert os.sched_getaffinity(s.pid) == {cpu}
        assert bc.sha(pathlib.Path('/proc', str(s.pid), 'exe')) == build['variants'][variant]['postgres_sha256']
        s.sql(SETTINGS)
        save()
        return item, s

    def stop(item):
        if item.get('stopped'): return
        s = sessions.pop(item['label'], None)
        if s: s.close(failed=state['status'].startswith('FAILED'))
        data, prefix = pathlib.Path(item['data']), pathlib.Path(item['prefix'])
        assert data.parent == out
        if (data / 'postmaster.pid').exists():
            pid = int((data / 'postmaster.pid').read_text().splitlines()[0])
            assert item.get('pid', pid) == pid
            assert bc.sha(pathlib.Path('/proc', str(pid), 'exe')) == build['variants'][item['variant']]['postgres_sha256']
            bc.run([prefix / 'bin/pg_ctl', '-D', data, '-m', 'fast', '-w', 'stop'],
                   out / (item['label'] + '-stop.log'), prefix=prefix, timeout=120)
        item['stop_proof'] = bc.stopped(prefix, data)
        assert not list(pathlib.Path(item['socket']).glob('.s.PGSQL.*'))
        for field in ['pid', 'backend_pid']:
            if field in item: assert not pathlib.Path('/proc', str(item[field])).exists()
        item['stopped'] = True
        save()

    def row_check(s, case):
        s.sql(SEQ)
        ref = s.sql(case['rows_sql'])
        seq_plan = s.json('EXPLAIN(FORMAT JSON) ' + case['sql'])[0]['Plan']
        assert any(n['Node Type'] == 'Seq Scan' for n in nodes(seq_plan))
        s.sql(GIN if case['indexed'] else SEQ)
        got = s.sql(case['rows_sql'])
        result = dict(reference=digest(ref), actual=digest(got))
        assert ref == got and result['reference']['rows'] == case['count']
        assert s.sql(case['sql']) == case['answer']
        tree = s.json('EXPLAIN(FORMAT JSON) ' + case['sql'])[0]['Plan']
        indexes = [n.get('Index Name') for n in nodes(tree) if n.get('Index Name')]
        assert ('large_d_gin' in indexes) if case['indexed'] else not indexes
        return result

    try:
        os.sched_setaffinity(0, {4})
        if args.large_from:
            prior = args.large_from.resolve()
            previous = json.loads((prior / 'status.json').read_text())
            assert args.mode == 'restart' and previous['status'] == 'PASS' and previous['mode'] == 'warm'
            assert not previous['cleanup_errors'] and previous['build_receipt_sha256'] == build_sha
            seed = prior / 'seed'
            seed_inventory = json.loads((prior / 'seed-manifest.json').read_text())
            bc.stopped(pathlib.Path(build['variants']['B']['prefix']), seed)
            assert bc.inventory(seed) == seed_inventory
            references = json.loads((prior / 'references.json').read_text())
            bc.save(out / 'seed-origin.json', dict(path=str(seed), prior_status_sha256=bc.sha(prior / 'status.json')))
            bc.save(out / 'seed-info.json', json.loads((prior / 'seed-info.json').read_text()))
        else:
            assert args.mode == 'warm'
            seed = out / 'seed'
            shutil.copytree(original_seed, seed)
            assert bc.inventory(seed) == original_inventory
            item, s = start('seed', 'B', seed, 0, args.first_port)
            s.sql("CREATE EXTENSION amcheck;CREATE TABLE g1.large_docs(id bigint,d tsvector);"
                  "INSERT INTO g1.large_docs SELECT g,to_tsvector('simple','common '||"
                  "CASE WHEN g%2=0 THEN 'dense2 ' ELSE '' END||CASE WHEN g%3=0 THEN 'dense3 ' ELSE '' END||"
                  "CASE WHEN g%1000=0 THEN 'rare0 ' ELSE '' END||CASE WHEN g%127=0 THEN 'rare2 ' ELSE '' END||"
                  "'group'||(g%4096)::text) FROM generate_series(1,1000000)g;"
                  "CREATE INDEX large_d_gin ON g1.large_docs USING gin(d) WITH(fastupdate=off);"
                  "VACUUM(FREEZE,ANALYZE) g1.large_docs")
            info = s.json("SELECT json_build_object('rows',(SELECT count(*) FROM g1.large_docs),"
                          "'table_bytes',pg_table_size('g1.large_docs'),'index_bytes',pg_relation_size('g1.large_d_gin'),"
                          "'shared_buffers_bytes',pg_size_bytes(current_setting('shared_buffers')),'version',version())")
            bc.save(out / 'seed-info.json', info)
            assert info['rows'] == spec['rows'] and info['table_bytes'] + info['index_bytes'] > info['shared_buffers_bytes']
            assert s.sql("SELECT gin_index_check('g1.large_d_gin')") == ''
            references = {c['name']: row_check(s, c) for c in spec['cases']}
            s.sql('CHECKPOINT')
            stop(item)
            seed_inventory = bc.inventory(seed)
        bc.save(out / 'references.json', references)
        bc.save(out / 'seed-manifest.json', seed_inventory)
        roles = spec['roles']
        for cohort in range(2):
            cpu, client = (0, 4) if cohort == 0 else (4, 0)
            os.sched_setaffinity(0, {client})
            bc.save(out / f'host-before-c{cohort}.json', host())
            mapping = dict(zip(roles, range(4) if cohort == 0 else reversed(range(4))))
            bc.save(out / f'role-map-c{cohort}.json', mapping)
            data_by_role = {}
            for role in sorted(roles, key=mapping.get):
                data = out / ('d%d%d' % (cohort, mapping[role]))
                shutil.copytree(seed, data)
                assert bc.inventory(data) == seed_inventory
                bc.sync(data)
                data_by_role[role] = data
            active = {}
            try:
                for role in sorted(roles, key=mapping.get):
                    item, s = start(f'q{cohort}{role}', spec['variants'][role], data_by_role[role], cpu,
                                     args.first_port + 10 + 4*cohort + mapping[role])
                    active[role] = item, s
                    got = {c['name']: row_check(s, c) for c in spec['cases']}
                    bc.save(out / f'qual-c{cohort}-{role}.json', got)
                    assert all(got[name] == references[name] for name in got)
                    if args.mode == 'restart': stop(item)
                ordered_cases = spec['cases'] if cohort == 0 else list(reversed(spec['cases']))
                with (out / f'raw-c{cohort}.jsonl').open('x') as stream, (out / f'answers-c{cohort}.jsonl').open('x') as answers_stream:
                    for ix, case in enumerate(ordered_cases):
                        for round_ in range(spec['warmups'] + spec['retained_rounds']):
                            order = spec['orders'][(round_ if round_ < 2 else round_-2) % 4]
                            for position, role in enumerate(order):
                                if args.mode == 'restart':
                                    item, s = start(f'r{cohort}{ix}{round_}{role}', spec['variants'][role], data_by_role[role], cpu,
                                                     args.first_port + 10 + 4*cohort + mapping[role])
                                    active[role] = item, s
                                else:
                                    item, s = active[role]
                                s.sql(GIN if case['indexed'] else SEQ)
                                if args.mode == 'warm': assert s.sql(case['sql']) == case['answer']
                                observed = s.measured('EXPLAIN(ANALYZE,BUFFERS,WAL,TIMING OFF,FORMAT JSON) ' + case['sql'])
                                row = dict(cohort=cohort, case=case['name'], role=role, round=round_, position=position,
                                           order=order, retained=round_ >= 2, observed=observed)
                                stream.write(json.dumps(row)+'\n')
                                stream.flush()
                                os.fsync(stream.fileno())
                                samples.append(row)
                                result = json.loads(observed['raw_result'])[0]
                                indexes = [n['Index Name'] for n in nodes(result['Plan']) if 'Index Name' in n]
                                assert ('large_d_gin' in indexes) if case['indexed'] else not indexes
                                assert result['Execution Time'] > 0 and observed['command_delta']['cpu_ns'] > 0
                                assert all(v >= 0 for v in observed['command_delta'].values())
                                actual_answer = s.sql(case['sql'])
                                answers_stream.write(json.dumps(dict(cohort=cohort, case=case['name'], role=role,
                                    round=round_, actual=actual_answer, expected=case['answer']))+'\n')
                                answers_stream.flush()
                                os.fsync(answers_stream.fileno())
                                assert actual_answer == case['answer']
                                if args.mode == 'restart': stop(item)
                                state.update(samples=len(samples), phase=f'c{cohort}-{case["name"]}')
                                save()
            except BaseException:
                state['status'] = 'FAILED_PRESERVED'
                raise
            finally:
                for item, s in reversed(list(active.values())): stop(item)
            bc.save(out / f'host-after-c{cohort}.json', host())
        assert len(samples) == spec['raw'] and sum(x['retained'] for x in samples) == spec['retained']
        absolute, pairs = [], []
        for cohort in range(2):
            for case in spec['cases']:
                for metric in ['backend_cpu_ms', 'client_wall_ms', 'executor_ms', 'shared_hit_blocks', 'shared_read_blocks', 'runqueue_ms']:
                    def value(row):
                        obs = row['observed']
                        if metric == 'backend_cpu_ms': return obs['command_delta']['cpu_ns']/1e6
                        if metric == 'client_wall_ms': return obs['client_ns']/1e6
                        if metric == 'runqueue_ms': return obs['command_delta']['runqueue_ns']/1e6
                        result = json.loads(obs['raw_result'])[0]
                        if metric == 'executor_ms': return result['Execution Time']
                        return result['Plan']['Shared Hit Blocks' if metric == 'shared_hit_blocks' else 'Shared Read Blocks']
                    points = {(x['round'], x['role']): value(x) for x in samples
                              if x['cohort'] == cohort and x['case'] == case['name'] and x['retained']}
                    rounds = range(2, 2+spec['retained_rounds'])
                    for role in roles:
                        absolute.append(dict(cohort=cohort, case=case['name'], metric=metric, role=role,
                                             **spread([points[r, role] for r in rounds])))
                    for left, right in itertools.combinations(roles, 2):
                        percent = [100*(points[r, right]/points[r, left]-1) for r in rounds] if all(points[r, left] > 0 for r in rounds) else None
                        pairs.append(dict(cohort=cohort, case=case['name'], metric=metric, left=left, right=right,
                                          percent=spread(percent) if percent is not None else None,
                                          delta=spread([points[r, right]-points[r, left] for r in rounds])))
        bc.save(out / 'absolute.json', absolute)
        bc.save(out / 'pairs.json', pairs)
        assert bc.inventory(seed) == seed_inventory and bc.inventory(original_seed) == original_inventory
        assert bc.inventory(source) == source_manifest
        bc.checked_build(args.build)
        for name, value in frozen.items():
            assert bc.sha(ROOT/name) == value['sha256'] and (ROOT/name).stat().st_size == value['bytes']
        state.update(status='PASS', raw=spec['raw'], retained=spec['retained'], warm=spec['warm'],
                     source_seed_and_installed_trees_unchanged=True, finished_ns=time.time_ns(), host_after=host())
    except BaseException as exc:
        state.update(status='FAILED_PRESERVED', error=repr(exc), traceback=traceback.format_exc())
        raise
    finally:
        errors = []
        for item in reversed(owned):
            try: stop(item)
            except BaseException as exc: errors.append(dict(label=item['label'], error=repr(exc)))
        state['cleanup_errors'] = errors
        if errors: state['status'] = 'FAILED_CLEANUP'
        save()
        if errors and not sys.exc_info()[0]: raise RuntimeError(errors)


if __name__ == '__main__': main()
