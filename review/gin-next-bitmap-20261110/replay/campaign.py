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
from protocol import plan as campaign_plan, micro_cases
from runtime_helpers import compile_micro, qualify_micro

loader = importlib.util.spec_from_file_location('build_common', HERE / 'build-harness/common.py')
bc = importlib.util.module_from_spec(loader)
loader.loader.exec_module(bc)


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
    parser.add_argument('--first-port', type=int, default=45500)
    parser.add_argument('--mode', choices=['qualify'], default='qualify')
    parser.set_defaults(qualified_from=None)
    args = parser.parse_args()
    protocol = campaign_plan(args.mode)
    ROLES = protocol['roles']
    out = args.output.resolve()
    out.mkdir()
    bc.nice10()
    assert {0, 4} <= os.sched_getaffinity(0)
    receipt = bc.checked_build(args.build)
    prefixes = {name: pathlib.Path(item['prefix']) for name, item in receipt['variants'].items()}
    final_source = json.loads((args.build / 'Bitmap_assert-source-inventory.json').read_text())
    assert bc.inventory(pathlib.Path(receipt['common_source'])) == final_source
    state = dict(status='RUNNING', phase='seed', build_receipt_sha256=bc.sha(args.build / 'build-receipt.json'),
                 source_plan_sha256=receipt['source_plan_sha256'], mode=args.mode, host_before=host(),
                 clusters=[], cleanup=[], timing_samples=0)
    bc.save(out / 'status.json', state)
    scripts = {p.relative_to(HERE).as_posix(): dict(bytes=p.stat().st_size, sha256=bc.sha(p))
               for tree in ('harness', 'build-harness', 'build-source')
               for p in sorted((HERE / tree).rglob('*')) if p.is_file() and '__pycache__' not in p.parts}
    for name in ['campaign.py', 'runtime_helpers.py', 'gin-am-micro.c']:
        scripts[name] = dict(bytes=(HERE/name).stat().st_size, sha256=bc.sha(HERE/name))
    bc.save(out / 'frozen-inputs.json', scripts)
    bc.save(out / 'protocol.json', protocol)
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
        if args.qualified_from:
            origin = args.qualified_from.resolve()
            old_state = json.loads((origin / 'status.json').read_text())
            assert args.mode != 'qualify' and old_state['status'] == 'PASS' and old_state['mode'] == 'qualify'
            assert old_state['build_receipt_sha256'] == state['build_receipt_sha256'] and not old_state['cleanup_errors']
            module = origin / 'gin-am-micro.so'
            module_receipt = json.loads((origin / 'module.json').read_text())
            assert bc.sha(module) == module_receipt['module_sha256'] and bc.sha(HERE / 'gin-am-micro.c') == module_receipt['source_sha256']
            bc.save(out / 'module.json', module_receipt)
            seed = origin / 'seed'
            bc.stopped(prefixes['B'], seed)
            seed_manifest = json.loads((origin / 'seed-manifest.json').read_text())
            assert bc.inventory(seed) == seed_manifest
            bc.save(out / 'seed-manifest.json', seed_manifest)
            bc.save(out / 'seed-info.json', json.loads((origin / 'seed-info.json').read_text()))
            bc.save(out / 'seed-origin.json', dict(origin=str(origin), module=str(module), seed=str(seed), qualification_status_sha256=bc.sha(origin / 'status.json')))
        else:
            module = compile_micro(HERE, out, prefixes['B'], bc)
            seed = out / 'seed'
            bc.run([prefixes['B'] / 'bin/initdb', '-D', seed, '--no-locale', '--encoding=UTF8',
                    '--auth=trust', '--data-checksums'], out / 'seed-initdb.log', prefix=prefixes['B'])
            seed_item, dsn = start('seed', 'B', seed, 0, args.first_port)
            s = session('seed', 'B', dsn)
            try:
                s.sql((HERE / 'harness/inputs/setup.sql').read_text())
                s.sql("CREATE FUNCTION public.gin_am_micro(regclass,tsquery,integer) RETURNS jsonb AS '" + str(module) + "', 'gin_am_micro' LANGUAGE C STRICT")
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

        if args.qualified_from:
            origin = args.qualified_from.resolve()
            old_qualification = json.loads((origin / 'qualification-summary.json').read_text())
            assert old_qualification['status'] == 'PASS'
            reference, qualifications = old_qualification['reference'], old_qualification['variants']
            for variant, artifact in qualifications.items():
                assert bc.sha(artifact['path']) == artifact['sha256']
                proof = json.loads(pathlib.Path(artifact['path']).read_text())
                assert proof['status'] == 'PASS' and proof['postgres_sha256'] == receipt['variants'][variant]['postgres_sha256']
            bc.save(out / 'qualification-summary.json', old_qualification)
        else:
            state['phase'] = 'ordinary-qualification'
            bc.save(out / 'status.json', state)
            reference, qualifications = {}, {}
            prepared_queries = ['common & rare0', 'common & rare1', 'common & group17',
                                'dense2 & dense3', 'common', 'common | rare0',
                                'dense2 <-> rare0', 'missing']
            for ix, variant in enumerate(['B','Bitmap','Bitmap_assert']):
                label = 'qual-' + variant
                item, dsn = start(label, variant, clone(label), 0, args.first_port + 1 + ix)
                s = session(label, variant, dsn)
                result = dict(status='RUNNING', variant=variant, source_commit=receipt['variants'][variant]['commit'],
                              postgres_sha256=receipt['variants'][variant]['postgres_sha256'],
                              cases={}, prepared={}, asserts=s.sql('SHOW debug_assertions'))
                try:
                    assert (result['asserts'] == 'on') == (variant == 'Bitmap_assert')
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
                    result['micro'] = qualify_micro(s, micro_cases())
                    result['lossy_prefix'] = {}
                    for pname, predicate, count, scalar in [
                            ('prefix_all', 'group:*', 200000, '200000|20000100000'),
                            ('prefix_and', 'group:* & rare0', 200, '200|20100000')]:
                        rows_sql = "SELECT id FROM g1.docs WHERE d @@ '" + predicate + "'::tsquery ORDER BY id"
                        aggregate = "SELECT count(*),sum(id) FROM g1.docs WHERE d @@ '" + predicate + "'::tsquery"
                        s.sql(reset + seq)
                        ref = s.sql(rows_sql)
                        assert digest(ref)['rows'] == count and s.sql(aggregate) == scalar
                        s.sql(gin + "SET work_mem='64kB'")
                        actual = s.sql(rows_sql)
                        assert actual == ref and s.sql(aggregate) == scalar
                        plan = s.json('EXPLAIN(ANALYZE,BUFFERS,TIMING OFF,FORMAT JSON) ' + aggregate)[0]
                        assert any(x.get('Index Name') == 'docs_d_gin' for x in nodes(plan['Plan']))
                        lossy = sum(x.get('Lossy Heap Blocks', 0) for x in nodes(plan['Plan']))
                        if pname == 'prefix_all':
                            assert lossy > 0, (variant, pname, 'required actual lossy heap path')
                        result['lossy_prefix'][pname] = dict(**digest(actual), literal_answer=scalar,
                                work_mem='64kB', plan=plan, lossy_heap_blocks=lossy)
                    s.sql(reset)
                    result['backend_pid'] = s.pid
                    result['status'] = 'PASS'
                finally:
                    s.close(failed=result['status'] != 'PASS')
                    stop(item)
                    bc.save(out / (label + '.json'), result)
                qualifications[variant] = dict(path=str(out / (label + '.json')),
                                                sha256=bc.sha(out / (label + '.json')))
            bc.save(out / 'qualification-summary.json', dict(status='PASS', variants=qualifications,
                    ordered_seq_gin_comparisons=75, frozen_scalar_checks=75,
                    prepared_seq_gin_comparisons=24, reference=reference,
                    reference_rows_per_variant=sum(x['rows'] for x in reference.values())))

        for cohort in range(protocol['cohorts']):
            state['phase'] = 'cohort-' + str(cohort)
            state['host_cohort_' + str(cohort)] = host()
            bc.save(out / 'status.json', state)
            server_cpu, client_cpu = (0, 4) if cohort == 0 else (4, 0)
            os.sched_setaffinity(0, {client_cpu})
            # Create and fsync numbered physical copies before assigning roles.
            copies = [clone(f'c{cohort}-{n}') for n in range(len(ROLES))]
            mapping = dict(zip(ROLES, range(len(ROLES)) if cohort == 0 else reversed(range(len(ROLES)))))
            runtime = dict(status='QUALIFIED_FIXED_PERFORMANCE_INPUTS', mode=args.mode, base_commit=receipt['base'],
                           fix0001_sha256=receipt['fix0001_sha256'], cohort=cohort,
                           server_cpu=server_cpu, client_cpu=client_cpu, roles={},
                           slot_assignment=mapping, session_order=sorted(ROLES, key=mapping.get))
            current = []
            try:
                dsns = {}
                for role in sorted(ROLES, key=mapping.get):
                    variant = receipt['role_to_variant'][role]
                    item, dsns[role] = start(f'c{cohort}-{role}', variant, copies[mapping[role]], server_cpu,
                                            args.first_port + 10 + cohort * len(ROLES) + mapping[role])
                    current.append(item)
                for role in ROLES:
                    variant = receipt['role_to_variant'][role]
                    v = receipt['variants'][variant]
                    runtime['roles'][role] = dict(prefix=str(prefixes[variant]), dsn=dsns[role],
                        backend_sha256=v['postgres_sha256'], source_commit=v['commit'],
                        fix0001_sha256=receipt['fix0001_sha256'], correctness_status='PASS',
                        qualification_receipt_sha256=qualifications[variant]['sha256'])
                runtime_path = out / ('runtime-c' + str(cohort) + '.json')
                bc.save(runtime_path, runtime)
                bc.run(['python3', '-B', HERE / 'harness/run.py', '--runtime', runtime_path,
                        '--cohort', cohort, '--out-new', out / ('cohort' + str(cohort))],
                       out / ('cohort' + str(cohort) + '-run.log'), timeout=14400)
                bc.run(['python3', '-B', HERE / 'harness/analyze-repair.py', out / ('cohort' + str(cohort)),
                        out / ('analysis' + str(cohort))], out / ('cohort' + str(cohort) + '-analyze.log'))
                state['timing_samples'] += protocol['raw'] // 2
            finally:
                for item in reversed(current):
                    stop(item)
            assert bc.inventory(seed) == seed_manifest

        bc.checked_build(args.build)
        assert bc.inventory(pathlib.Path(receipt['common_source'])) == final_source
        state['full_source_unchanged'] = True
        assert bc.sha(module) == json.loads((out / 'module.json').read_text())['module_sha256']
        state['actual_am_module_unchanged'] = True
        assert bc.inventory(seed) == seed_manifest
        for name, value in scripts.items():
            assert (HERE / name).stat().st_size == value['bytes'] and bc.sha(HERE / name) == value['sha256']
        state.update(status='PASS', mode=args.mode, raw=protocol['raw'], retained=protocol['retained'], warm=protocol['warm'], host_after=host(),
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
