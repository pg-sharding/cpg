#!/usr/bin/env python3
"""Finite ordinary GIN SQL campaign, with owned clusters and immutable seed."""
import argparse
import hashlib
import importlib.util
import json
import os
import pathlib
import shutil
import subprocess
import sys
import time
import traceback

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / 'harness'))
from session import Session

loader = importlib.util.spec_from_file_location('build_common', HERE / 'build-harness/common.py')
bc = importlib.util.module_from_spec(loader)
loader.loader.exec_module(bc)
ROLES = ['B', 'T', 'L4', 'A4']


def host():
    return dict(uname=list(os.uname()), load=list(os.getloadavg()),
                affinity=sorted(os.sched_getaffinity(0)),
                memory={k: v.strip() for k, v in
                        (line.split(':', 1) for line in pathlib.Path('/proc/meminfo').read_text().splitlines())
                        if k in {'MemTotal', 'MemAvailable', 'SwapTotal', 'SwapFree'}},
                cpu_topology=subprocess.check_output(['lscpu', '-e=CPU,CORE,SOCKET,ONLINE'], text=True),
                realtime_ns=time.time_ns())


def digest(text):
    return dict(bytes=len(text.encode()), rows=len(text.splitlines()) if text else 0,
                sha256=hashlib.sha256(text.encode()).hexdigest())


def nodes(plan):
    yield plan
    for child in plan.get('Plans', []):
        yield from nodes(child)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--build', type=pathlib.Path, required=True)
    parser.add_argument('--output', type=pathlib.Path, required=True)
    parser.add_argument('--first-port', type=int, default=41800)
    args = parser.parse_args()
    out = args.output.resolve()
    out.mkdir()
    bc.nice10()
    assert {0, 4} <= os.sched_getaffinity(0)
    receipt = bc.checked_build(args.build)
    prefixes = {name: pathlib.Path(item['prefix']) for name, item in receipt['variants'].items()}
    state = dict(status='RUNNING', phase='seed', build_receipt_sha256=bc.sha(args.build / 'build-receipt.json'),
                 source_plan_sha256=receipt['source_plan_sha256'], host_before=host(),
                 clusters=[], cleanup=[], timing_samples=0)
    bc.save(out / 'status.json', state)
    scripts = {p.relative_to(HERE).as_posix(): dict(bytes=p.stat().st_size, sha256=bc.sha(p))
               for tree in ('harness', 'build-harness', 'build-source')
               for p in sorted((HERE / tree).rglob('*')) if p.is_file() and '__pycache__' not in p.parts}
    scripts['campaign.py'] = dict(bytes=pathlib.Path(__file__).stat().st_size, sha256=bc.sha(__file__))
    bc.save(out / 'frozen-inputs.json', scripts)
    cases = (json.loads((HERE / 'harness/inputs/queries.json').read_text())['cases'] +
             json.loads((HERE / 'harness/inputs/queries-holdout.json').read_text())['cases'])
    answers = json.loads((HERE / 'harness/inputs/answers.json').read_text())
    assert len(cases) == 25
    seq = 'SET enable_seqscan=on;SET enable_bitmapscan=off;SET enable_indexscan=off;SET enable_indexonlyscan=off;'
    gin = 'SET enable_seqscan=off;SET enable_bitmapscan=on;SET enable_indexscan=off;SET enable_indexonlyscan=off;'
    reset = "RESET enable_seqscan;RESET enable_bitmapscan;RESET enable_indexscan;RESET enable_indexonlyscan;SET work_mem='64MB';"
    settings = ("SET search_path=g1,public,pg_catalog;SET jit=off;SET max_parallel_workers_per_gather=0;"
                "SET enable_memoize=off;SET gin_fuzzy_search_limit=0;SET statement_timeout='180s';"
                "SET lock_timeout='10s';SET work_mem='64MB';")
    owned = []

    def start(label, variant, data, cpu, port):
        prefix = prefixes[variant]
        sock = bc.socket_directory(out / ('s-' + label), port)
        item = dict(label=label, variant=variant, prefix=str(prefix), data=str(data), socket=str(sock), port=port,
                    server_cpu=cpu, before_ns=time.time_ns())
        owned.append(item)
        state['clusters'].append(item)
        bc.save(out / 'status.json', state)
        opts = (f'-p {port} -k {sock} -c listen_addresses= -c shared_buffers=512MB '
                '-c autovacuum=off -c jit=off -c max_parallel_workers_per_gather=0 '
                '-c max_parallel_workers=0 -c max_parallel_maintenance_workers=0 '
                '-c max_connections=12 -c huge_pages=off -c timing_clock_source=system '
                '-c checkpoint_timeout=1h -c max_wal_size=2GB')
        bc.run(['taskset', '-c', str(cpu), prefix / 'bin/pg_ctl', '-D', data,
                '-l', out / (label + '-server.log'), '-o', opts, '-w', 'start'],
               out / (label + '-start.log'), prefix=prefix, timeout=120)
        item['pid'] = int((data / 'postmaster.pid').read_text().splitlines()[0])
        assert bc.sha(pathlib.Path('/proc', str(item['pid']), 'exe')) == bc.sha(prefix / 'bin/postgres')
        assert os.sched_getaffinity(item['pid']) == {cpu}
        item['ready_ns'] = time.time_ns()
        bc.save(out / 'status.json', state)
        return item, bc.local_dsn(sock, port)

    def stop(item):
        data, prefix = pathlib.Path(item['data']), pathlib.Path(item['prefix'])
        if item.get('stopped'):
            return
        assert data.parent == out
        if (data / 'postmaster.pid').exists():
            pid = int((data / 'postmaster.pid').read_text().splitlines()[0])
            assert bc.sha(pathlib.Path('/proc', str(pid), 'exe')) == bc.sha(prefix / 'bin/postgres')
            bc.run([prefix / 'bin/pg_ctl', '-D', data, '-m', 'fast', '-w', 'stop'],
                   out / (item['label'] + '-stop.log'), prefix=prefix, timeout=120)
        proof = bc.stopped(prefix, data)
        assert not pathlib.Path(item['socket'], '.s.PGSQL.' + str(item['port'])).exists()
        if item.get('pid'):
            assert not pathlib.Path('/proc', str(item['pid'])).exists()
        item.update(stopped=True, stop_proof=proof, stopped_ns=time.time_ns())
        state['cleanup'].append(dict(label=item['label'], **proof))
        bc.save(out / 'status.json', state)

    def session(label, variant, dsn):
        s = Session(prefixes[variant], dsn, out / (label + '-psql-stderr.txt'))
        s.pid = int(s.sql('SELECT pg_backend_pid()'))
        assert os.sched_getaffinity(s.pid) == {0}
        assert bc.sha(pathlib.Path('/proc', str(s.pid), 'exe')) == receipt['variants'][variant]['postgres_sha256']
        s.sql(settings)
        return s

    try:
        os.sched_setaffinity(0, {4})
        seed = out / 'seed'
        bc.run([prefixes['B'] / 'bin/initdb', '-D', seed, '--no-locale', '--encoding=UTF8',
                '--auth=trust', '--data-checksums'], out / 'seed-initdb.log', prefix=prefixes['B'])
        seed_item, dsn = start('seed', 'B', seed, 0, args.first_port)
        s = session('seed', 'B', dsn)
        try:
            s.sql((HERE / 'harness/inputs/setup.sql').read_text())
            seed_info = s.json("SELECT json_build_object('version',version(),'clock',current_setting('timing_clock_source'),"
                               "'docs_rows',(SELECT count(*) FROM g1.docs),'docs_bytes',pg_total_relation_size('g1.docs'),"
                               "'database_bytes',pg_database_size(current_database()))")
            assert seed_info['docs_rows'] == 200002
            s.sql('CHECKPOINT')
            bc.save(out / 'seed-info.json', seed_info)
        finally:
            s.close()
            stop(seed_item)
        seed_manifest = bc.inventory(seed)
        bc.save(out / 'seed-manifest.json', seed_manifest)

        def clone(label):
            data = out / ('data-' + label)
            shutil.copytree(seed, data, symlinks=False)
            assert bc.inventory(data) == seed_manifest
            bc.sync(data)
            return data

        state['phase'] = 'ordinary-qualification'
        bc.save(out / 'status.json', state)
        reference, qualifications = {}, {}
        prepared_queries = ['common & rare0', 'common & rare1', 'common & group17',
                            'dense2 & dense3', 'common', 'common | rare0',
                            'dense2 <-> rare0', 'missing']
        for ix, variant in enumerate(['B', 'L4', 'A4', 'A4_assert']):
            label = 'qual-' + variant
            item, dsn = start(label, variant, clone(label), 0, args.first_port + 1 + ix)
            s = session(label, variant, dsn)
            result = dict(status='RUNNING', variant=variant, source_commit=receipt['variants'][variant]['commit'],
                          postgres_sha256=receipt['variants'][variant]['postgres_sha256'],
                          cases={}, prepared={}, asserts=s.sql('SHOW debug_assertions'))
            try:
                assert (result['asserts'] == 'on') == (variant == 'A4_assert')
                for case in cases:
                    s.sql(reset + seq)
                    query = 'SELECT id FROM (' + case['rows_sql'] + ') q ORDER BY id'
                    ref = s.sql(query)
                    s.sql(gin)
                    actual = s.sql(query)
                    assert ref == actual, (variant, case['name'], 'ordered Seq/GIN multiset')
                    key = digest(ref)
                    if variant == 'B':
                        reference[case['name']] = key
                    assert key == reference[case['name']], (variant, case['name'], 'cross-role multiset')
                    s.sql(reset + case['settings'])
                    scalar = s.sql(case['sql'])
                    assert scalar == answers[case['name']], (variant, case['name'], 'frozen scalar')
                    plan = s.json('EXPLAIN(FORMAT JSON) ' + case['sql'])[0]['Plan']
                    indexes = [n['Index Name'] for n in nodes(plan) if 'Index Name' in n]
                    assert (case['index'] in indexes) if case['index'] else not indexes
                    result['cases'][case['name']] = dict(**key, literal_answer=scalar, indexes=indexes)
                s.sql(reset + "SET plan_cache_mode=force_generic_plan;PREPARE ordinary_gin(tsquery) AS SELECT id FROM g1.docs WHERE d @@ $1 ORDER BY id")
                for text in prepared_queries:
                    query = "EXECUTE ordinary_gin('" + text + "'::tsquery)"
                    s.sql(seq + 'DISCARD PLANS')
                    ref = s.sql(query)
                    ref_plan = s.json('EXPLAIN(FORMAT JSON) ' + query)[0]['Plan']
                    assert any(n['Node Type'] == 'Seq Scan' for n in nodes(ref_plan))
                    s.sql(gin + 'DISCARD PLANS')
                    actual = s.sql(query)
                    assert ref == actual, (variant, text, 'prepared rescan multiset')
                    actual_plan = s.json('EXPLAIN(FORMAT JSON) ' + query)[0]['Plan']
                    assert any(n.get('Index Name') == 'docs_d_gin' for n in nodes(actual_plan))
                    assert s.sql(query) == ref, (variant, text, 'cached plan rescan')
                    result['prepared'][text] = dict(**digest(actual), seq_and_gin_paths_verified=True,
                                                   repeated_cached_execution_equal=True)
                s.sql('DEALLOCATE ordinary_gin')
                result['status'] = 'PASS'
            finally:
                s.close(failed=result['status'] != 'PASS')
                stop(item)
                bc.save(out / (label + '.json'), result)
            qualifications[variant] = dict(path=str(out / (label + '.json')),
                                            sha256=bc.sha(out / (label + '.json')))
        bc.save(out / 'qualification-summary.json', dict(status='PASS', variants=qualifications,
                ordered_seq_gin_comparisons=100, frozen_scalar_checks=100,
                prepared_seq_gin_comparisons=32, reference=reference,
                reference_rows_per_variant=sum(x['rows'] for x in reference.values())))

        for cohort in [0, 1]:
            state['phase'] = 'cohort-' + str(cohort)
            state['host_cohort_' + str(cohort)] = host()
            bc.save(out / 'status.json', state)
            server_cpu, client_cpu = (0, 4) if cohort == 0 else (4, 0)
            os.sched_setaffinity(0, {client_cpu})
            # Create and fsync numbered physical copies before assigning roles.
            copies = [clone(f'c{cohort}-{n}') for n in range(4)]
            mapping = dict(zip(ROLES, [0, 1, 2, 3] if cohort == 0 else [3, 2, 1, 0]))
            runtime = dict(status='QUALIFIED_FIXED_PERFORMANCE_INPUTS', base_commit=receipt['base'],
                           fix0001_sha256=receipt['fix0001_sha256'], cohort=cohort,
                           server_cpu=server_cpu, client_cpu=client_cpu, roles={},
                           slot_assignment=mapping, session_order=sorted(ROLES, key=mapping.get))
            current = []
            try:
                dsns = {}
                for role in sorted(ROLES, key=mapping.get):
                    variant = 'B' if role == 'T' else role
                    item, dsns[role] = start(f'c{cohort}-{role}', variant, copies[mapping[role]], server_cpu,
                                            args.first_port + 10 + cohort * 4 + mapping[role])
                    current.append(item)
                for role in ROLES:
                    variant = 'B' if role == 'T' else role
                    v = receipt['variants'][variant]
                    runtime['roles'][role] = dict(prefix=str(prefixes[variant]), dsn=dsns[role],
                        backend_sha256=v['postgres_sha256'], source_commit=v['commit'],
                        fix0001_sha256=receipt['fix0001_sha256'], correctness_status='PASS',
                        qualification_receipt_sha256=qualifications[variant]['sha256'])
                runtime_path = out / ('runtime-c' + str(cohort) + '.json')
                bc.save(runtime_path, runtime)
                bc.run(['python3', '-B', HERE / 'harness/run-sql.py', '--runtime', runtime_path,
                        '--cohort', cohort, '--out-new', out / ('cohort' + str(cohort))],
                       out / ('cohort' + str(cohort) + '-run.log'), timeout=14400)
                bc.run(['python3', '-B', HERE / 'harness/analyze.py', out / ('cohort' + str(cohort)),
                        out / ('analysis' + str(cohort))], out / ('cohort' + str(cohort) + '-analyze.log'))
                state['timing_samples'] += 1400
            finally:
                for item in reversed(current):
                    stop(item)
            assert bc.inventory(seed) == seed_manifest

        bc.checked_build(args.build)
        assert bc.inventory(seed) == seed_manifest
        for name, value in scripts.items():
            assert (HERE / name).stat().st_size == value['bytes'] and bc.sha(HERE / name) == value['sha256']
        state.update(status='PASS', raw=2800, retained=2400, warm=400, host_after=host(),
                     fixture_unchanged=True, installed_trees_unchanged=True,
                     frozen_runtime_unchanged=True, finished_ns=time.time_ns())
    except BaseException as exc:
        state.update(status='FAILED_PRESERVED', error=repr(exc), traceback=traceback.format_exc(),
                     finished_ns=time.time_ns())
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
        bc.save(out / 'status.json', state)
        if errors and not sys.exc_info()[0]:
            raise RuntimeError(errors)
    print(json.dumps(dict(status=state['status'], raw=state['raw'], clusters=len(owned))))


if __name__ == '__main__':
    main()
