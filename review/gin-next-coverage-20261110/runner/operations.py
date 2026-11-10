#!/usr/bin/env python3
"""Finite CREATE INDEX / INSERT / VACUUM controls for the C11 builds."""
import argparse
import hashlib
import importlib.util
import itertools
import json
import os
import pathlib
import shutil
import statistics
import subprocess
import sys
import time
import traceback

ROOT = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'harness'))
from session import Session
from protocol import plan

loader = importlib.util.spec_from_file_location('build_common', ROOT / 'build-harness/common.py')
bc = importlib.util.module_from_spec(loader)
loader.loader.exec_module(bc)


def spread(values):
    median = statistics.median(values)
    return dict(n=len(values), min=min(values), median=median, max=max(values),
                mean=statistics.mean(values), stdev=statistics.stdev(values),
                MAD=statistics.median(abs(x - median) for x in values), values=values)


def digest(value):
    return dict(rows=len(value.splitlines()) if value else 0,
                sha256=hashlib.sha256(value.encode()).hexdigest())


def nodes(node):
    yield node
    for child in node.get('Plans', []):
        yield from nodes(child)


def host():
    return dict(load=list(os.getloadavg()), realtime_ns=time.time_ns(),
                topology=subprocess.check_output(['lscpu', '-e=CPU,CORE,SOCKET,ONLINE'], text=True),
                memory={k: v.strip() for k, v in
                        (line.split(':', 1) for line in pathlib.Path('/proc/meminfo').read_text().splitlines())
                        if k in {'MemTotal', 'MemAvailable', 'SwapTotal', 'SwapFree'}})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--operation', choices=['create-index', 'insert', 'vacuum'], required=True)
    parser.add_argument('--build', type=pathlib.Path, required=True)
    parser.add_argument('--qualified-from', type=pathlib.Path, required=True)
    parser.add_argument('--output', type=pathlib.Path, required=True)
    parser.add_argument('--first-port', type=int, default=45700)
    args = parser.parse_args()
    spec = plan(args.operation)
    out = args.output.resolve()
    out.mkdir()
    bc.nice10()
    assert {0, 4} <= os.sched_getaffinity(0)
    build = bc.checked_build(args.build)
    origin = args.qualified_from.resolve()
    qualification = json.loads((origin / 'status.json').read_text())
    assert qualification['status'] == 'PASS' and qualification['mode'] == 'qualify'
    assert not qualification['cleanup_errors']
    assert qualification['build_receipt_sha256'] == bc.sha(args.build / 'build-receipt.json')
    source = pathlib.Path(build['common_source'])
    original_source = json.loads((args.build / 'C11_assert-source-inventory.json').read_text())
    assert bc.inventory(source) == original_source
    seed = origin / 'seed'
    original = json.loads((origin / 'seed-manifest.json').read_text())
    assert bc.inventory(seed) == original
    bc.stopped(pathlib.Path(build['variants']['B']['prefix']), seed)
    bc.save(out / 'input-seed-manifest.json', original)
    bc.save(out / 'protocol.json', spec)
    scripts = [pathlib.Path(__file__), ROOT / 'protocol.py', ROOT / 'harness/session.py',
               ROOT / 'harness/common.py', ROOT / 'build-harness/common.py']
    frozen = {str(p.relative_to(ROOT)): dict(bytes=p.stat().st_size, sha256=bc.sha(p)) for p in scripts}
    bc.save(out / 'frozen-inputs.json', frozen)
    bc.save(out / 'provenance.json', dict(build=str(args.build.resolve()),
            build_receipt_sha256=bc.sha(args.build / 'build-receipt.json'),
            qualified_from=str(origin), qualification_sha256=bc.sha(origin / 'status.json')))
    state = dict(status='RUNNING', phase='seed', clusters=[], started_ns=time.time_ns(),
                 samples=0, host_before=host())
    owned, sessions, rows = [], {}, []
    bc.save(out / 'status.json', state)
    settings = ("SET search_path=g1,public,pg_catalog;SET jit=off;SET max_parallel_workers_per_gather=0;"
                "SET max_parallel_maintenance_workers=0;SET maintenance_work_mem='128MB';"
                "SET gin_fuzzy_search_limit=0;SET work_mem='64MB';SET statement_timeout='180s';SET lock_timeout='10s'")
    seq = 'SET enable_seqscan=on;SET enable_bitmapscan=off;SET enable_indexscan=off;SET enable_indexonlyscan=off'
    gin = 'SET enable_seqscan=off;SET enable_bitmapscan=on;SET enable_indexscan=off;SET enable_indexonlyscan=off'

    def save():
        bc.save(out / 'status.json', state)

    def start(label, variant, data, cpu, port):
        prefix = pathlib.Path(build['variants'][variant]['prefix'])
        sock = bc.socket_directory(out / ('s-' + label), port)
        item = dict(label=label, variant=variant, prefix=str(prefix), data=str(data), socket=str(sock), port=port)
        owned.append(item)
        state['clusters'].append(item)
        save()
        options = (f'-p {port} -k {sock} -c listen_addresses= -c shared_buffers=512MB '
                   '-c autovacuum=off -c jit=off -c max_parallel_workers=0 -c max_parallel_maintenance_workers=0 '
                   '-c max_connections=12 -c huge_pages=off -c timing_clock_source=system '
                   '-c checkpoint_timeout=1h -c max_wal_size=2GB')
        bc.run(['taskset', '-c', cpu, prefix / 'bin/pg_ctl', '-D', data, '-l', out / (label + '-server.log'),
                '-o', options, '-w', 'start'], out / (label + '-start.log'), prefix=prefix, timeout=120)
        item['pid'] = int((data / 'postmaster.pid').read_text().splitlines()[0])
        assert os.sched_getaffinity(item['pid']) == {cpu}
        assert bc.sha(pathlib.Path('/proc', str(item['pid']), 'exe')) == build['variants'][variant]['postgres_sha256']
        s = Session(prefix, bc.local_dsn(sock, port), out / (label + '-stderr.txt'))
        sessions[label] = s
        s.pid = int(s.sql('SELECT pg_backend_pid()'))
        item['backend_pid'] = s.pid
        assert os.sched_getaffinity(s.pid) == {cpu}
        assert bc.sha(pathlib.Path('/proc', str(s.pid), 'exe')) == build['variants'][variant]['postgres_sha256']
        s.sql(settings)
        save()
        return item, s

    def stop(item):
        if item.get('stopped'):
            return
        s = sessions.pop(item['label'], None)
        if s:
            s.close(failed=state['status'].startswith('FAILED'))
        prefix, data = pathlib.Path(item['prefix']), pathlib.Path(item['data'])
        assert data.parent == out
        if (data / 'postmaster.pid').exists():
            pid = int((data / 'postmaster.pid').read_text().splitlines()[0])
            assert item.get('pid', pid) == pid
            assert bc.sha(pathlib.Path('/proc', str(pid), 'exe')) == build['variants'][item['variant']]['postgres_sha256']
            bc.run([prefix / 'bin/pg_ctl', '-D', data, '-m', 'fast', '-w', 'stop'],
                   out / (item['label'] + '-stop.log'), prefix=prefix, timeout=120)
        item['stop_proof'] = bc.stopped(prefix, data)
        for key in ['pid', 'backend_pid']:
            if key in item:
                assert not pathlib.Path('/proc', str(item[key])).exists()
        assert not list(pathlib.Path(item['socket']).glob('.s.PGSQL.*'))
        item['stopped'] = True
        save()

    relation = 'g1.' + spec['relation']
    index = 'g1.bench_idx'

    def references(s):
        s.sql(seq)
        result = {}
        for query, expected in zip(spec['queries'], spec['expected_rows']):
            value = digest(s.sql(f"SELECT id FROM {relation} WHERE d @@ '{query}'::tsquery ORDER BY id"))
            assert value['rows'] == expected, (query, value, expected)
            result[query] = value
        return result

    def prepare(s):
        s.sql('RESET enable_seqscan;RESET enable_bitmapscan;RESET enable_indexscan;RESET enable_indexonlyscan')
        if args.operation != 'create-index':
            s.sql('TRUNCATE g1.write_bench')
        if args.operation == 'vacuum':
            s.sql('INSERT INTO g1.write_bench SELECT id,d FROM g1.docs WHERE id BETWEEN 1 AND 20000 ORDER BY id;'
                  'DELETE FROM g1.write_bench WHERE id%2=0')

    def shape(s):
        return s.json(f"SELECT json_build_object('rows',(SELECT count(*) FROM {relation}),"
                      f"'heap_bytes',pg_relation_size('{relation}'),'index_bytes',pg_relation_size('{index}'),"
                      "'estimated_rows',c.reltuples,'heap_pages',c.relpages,'all_visible',c.relallvisible) "
                      f"FROM pg_class c WHERE c.oid='{relation}'::regclass")

    def check(s, ref):
        assert s.sql(f"SELECT gin_index_check('{index}')") == ''
        assert int(s.sql(f'SELECT count(*) FROM {relation}')) == spec['expected_table_rows']
        assert references(s) == ref
        s.sql(gin)
        for query in spec['queries']:
            sql = f"SELECT id FROM {relation} WHERE d @@ '{query}'::tsquery ORDER BY id"
            assert digest(s.sql(sql)) == ref[query]
            tree = s.json('EXPLAIN(FORMAT JSON) ' + sql)[0]['Plan']
            assert any(n.get('Index Name') == 'bench_idx' for n in nodes(tree))
        return shape(s)

    observations = out / 'observations'
    observations.mkdir()
    command_serial = 0

    def one(s, ref, identity):
        nonlocal command_serial
        command_serial += 1
        evidence = observations / ('command-%04d.json' % command_serial)
        prepare(s)
        lsn = s.sql('SELECT pg_current_wal_insert_lsn()')
        observed = s.measured(spec['command'])
        partial = dict(status='MEASURED_PENDING_WAL', command=spec['command'], identity=identity, observed=observed)
        bc.save(evidence, partial)
        assert observed['raw_result'] == ''
        assert observed['client_ns'] > 0 and observed['command_delta']['cpu_ns'] > 0
        assert all(v >= 0 for v in observed['command_delta'].values())
        wal = int(s.sql(f"SELECT pg_wal_lsn_diff(pg_current_wal_insert_lsn(),'{lsn}'::pg_lsn)::bigint"))
        partial.update(status='OBSERVED_PENDING_VALIDATION', wal_bytes=wal)
        bc.save(evidence, partial)
        assert wal >= 0
        after = check(s, ref)
        if args.operation == 'create-index':
            s.sql('DROP INDEX g1.bench_idx')
        partial.update(status='PASS', after=after)
        bc.save(evidence, partial)
        return dict(observed=observed, wal_bytes=wal, after=after,
                    validation='amcheck + table count + ordered Seq/GIN digest + forced index plan PASS')

    try:
        os.sched_setaffinity(0, {4})
        prepared = out / 'seed'
        shutil.copytree(seed, prepared)
        assert bc.inventory(prepared) == original
        item, s = start('seed', 'B', prepared, 0, args.first_port)
        s.sql('CREATE EXTENSION amcheck')
        if args.operation == 'create-index':
            s.sql('DROP INDEX g1.docs_d_gin')
        else:
            s.sql('CREATE TABLE g1.write_bench(id bigint,d tsvector);'
                  'CREATE INDEX bench_idx ON g1.write_bench USING gin(d) WITH(fastupdate=off)')
            if args.operation == 'insert':
                s.sql(spec['command'])
            else:
                prepare(s)
        ref = references(s)
        bc.save(out / 'references.json', ref)
        if args.operation != 'create-index':
            s.sql('TRUNCATE g1.write_bench')
        s.sql('CHECKPOINT')
        stop(item)
        prepared_manifest = bc.inventory(prepared)
        bc.save(out / 'seed-manifest.json', prepared_manifest)
        roles, orders = spec['roles'], spec['orders']
        for cohort in range(spec['cohorts']):
            cpu, client = (0, 4) if cohort == 0 else (4, 0)
            os.sched_setaffinity(0, {client})
            state.update(phase='cohort-' + str(cohort), host_current=host())
            bc.save(out / f'host-before-c{cohort}.json', host())
            save()
            copies = []
            for slot in range(len(roles)):
                data = out / f'data-c{cohort}-{slot}'
                shutil.copytree(prepared, data)
                assert bc.inventory(data) == prepared_manifest
                bc.sync(data)
                copies.append(data)
            mapping = dict(zip(roles, range(len(roles)) if cohort == 0 else reversed(range(len(roles)))))
            bc.save(out / f'role-map-c{cohort}.json', mapping)
            active = {}
            try:
                for role in sorted(roles, key=mapping.get):
                    active[role] = start(f'c{cohort}-{role}', spec['variants'][role], copies[mapping[role]], cpu,
                                         args.first_port + 10 + cohort * len(roles) + mapping[role])
                # A complete untimed operation and validation on every new backend.
                bc.save(out / f'qualification-c{cohort}.json',
                        {role: one(s, ref, dict(cohort=cohort, role=role, phase='qualification'))
                         for role, (item, s) in active.items()})
                with (out / f'raw-c{cohort}.jsonl').open('x') as stream:
                    for round_ in range(spec['warmups'] + spec['retained_rounds']):
                        order = orders[(round_ if round_ < spec['warmups'] else round_ - spec['warmups']) % len(orders)]
                        for position, role in enumerate(order):
                            item, s = active[role]
                            record = dict(cohort=cohort, round=round_, role=role, position=position, order=order,
                                          retained=round_ >= spec['warmups'],
                                          **one(s, ref, dict(cohort=cohort, role=role, round=round_, phase='benchmark')))
                            stream.write(json.dumps(record) + '\n')
                            stream.flush()
                            os.fsync(stream.fileno())
                            rows.append(record)
                            state['samples'] = len(rows)
                            save()
            except BaseException:
                state['status'] = 'FAILED_PRESERVED'
                raise
            finally:
                for item, s in reversed(list(active.values())):
                    stop(item)
            bc.save(out / f'host-after-c{cohort}.json', host())
        assert len(rows) == spec['raw'] and sum(x['retained'] for x in rows) == spec['retained']
        absolute, pairs = [], []
        for cohort in range(spec['cohorts']):
            for metric in ['backend_cpu_ms', 'client_wall_ms', 'wal_bytes', 'read_bytes', 'write_bytes', 'runqueue_ms']:
                def get(row):
                    obs = row['observed']
                    if metric == 'backend_cpu_ms': return obs['command_delta']['cpu_ns'] / 1e6
                    if metric == 'client_wall_ms': return obs['client_ns'] / 1e6
                    if metric == 'runqueue_ms': return obs['command_delta']['runqueue_ns'] / 1e6
                    if metric == 'wal_bytes': return row['wal_bytes']
                    return obs['command_delta'][metric]
                points = {(x['round'], x['role']): get(x) for x in rows if x['cohort'] == cohort and x['retained']}
                rounds = range(spec['warmups'], spec['warmups'] + spec['retained_rounds'])
                for role in roles:
                    absolute.append(dict(cohort=cohort, role=role, metric=metric,
                                         **spread([points[r, role] for r in rounds])))
                for left, right in itertools.combinations(roles, 2):
                    defined = all(points[r, left] > 0 for r in rounds)
                    pairs.append(dict(cohort=cohort, left=left, right=right, metric=metric,
                                      percent=spread([100 * (points[r, right] / points[r, left] - 1) for r in rounds]) if defined else None,
                                      delta=spread([points[r, right] - points[r, left] for r in rounds])))
        bc.save(out / 'absolute.json', absolute)
        bc.save(out / 'pairs.json', pairs)
        assert bc.inventory(seed) == original and bc.inventory(prepared) == prepared_manifest
        assert bc.inventory(source) == original_source
        bc.checked_build(args.build)
        for name, value in frozen.items():
            assert bc.sha(ROOT / name) == value['sha256'] and (ROOT / name).stat().st_size == value['bytes']
        state.update(status='PASS', raw=spec['raw'], retained=spec['retained'], warm=spec['warm'],
                     original_source_and_seed_unchanged=True, installed_trees_unchanged=True,
                     finished_ns=time.time_ns(), host_after=host())
    except BaseException as exc:
        state.update(status='FAILED_PRESERVED', error=repr(exc), traceback=traceback.format_exc())
        raise
    finally:
        errors = []
        for item in reversed(owned):
            try:
                stop(item)
            except BaseException as exc:
                errors.append(dict(label=item['label'], error=repr(exc)))
        state['cleanup_errors'] = errors
        if errors and state['status'] == 'PASS':
            state['status'] = 'FAILED_CLEANUP'
        save()
        if errors and not sys.exc_info()[0]:
            raise RuntimeError(errors)


if __name__ == '__main__':
    main()
