#!/usr/bin/env python3
"""Finite untimed actual dispatcher captures, only after instrumented gate PASS."""
import argparse
import hashlib
import importlib.util
import json
import os
import pathlib
import shlex
import shutil
import sys
import time
import traceback

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / 'qualification'))
from session import Session
loader = importlib.util.spec_from_file_location('bc', HERE / 'build-harness/common.py')
bc = importlib.util.module_from_spec(loader)
loader.loader.exec_module(bc)
SEQ = 'SET enable_seqscan=on;SET enable_bitmapscan=off;SET enable_indexscan=off;SET enable_indexonlyscan=off;'
GIN = 'SET enable_seqscan=off;SET enable_bitmapscan=on;SET enable_indexscan=off;SET enable_indexonlyscan=off;'
RESET = "RESET enable_seqscan;RESET enable_bitmapscan;RESET enable_indexscan;RESET enable_indexonlyscan;SET work_mem='64MB';"
AM_REFERENCE = dict(am_dense='dense_and', am_rare='single_rare', am_full='single_forced',
                    am_or='or_forced', am_inline='inline', am_absent='absent')


def digest(text):
    return dict(bytes=len(text.encode()), rows=len(text.splitlines()) if text else 0,
                sha256=hashlib.sha256(text.encode()).hexdigest())


def nodes(node):
    yield node
    for child in node.get('Plans', []):
        yield from nodes(child)


def check_probe(probe, expected_keys, expected_entries):
    assert probe['scope'] == 'untimed instrumented K3 dispatcher only'
    assert probe['key_cap'] == 128 and probe['overflow'] == 0
    records = probe['records']
    assert len(records) == probe['keys'] == expected_keys
    assert [r['generation'] for r in records] == list(range(1, expected_keys + 1))
    for r in records:
        assert r['cache_installed'] is True and r['nuserentries'] == expected_entries
        assert r['contract_errors'] == r['overbound_dispatches'] == 0
        assert r['dispatches'] == r['cached_dispatches'] + r['direct_dispatches']
        assert r['native_calls'] == r['native_from_cache'] + r['direct_dispatches']
        assert r['native_from_cache'] == r['misses']
        assert r['dispatches'] == r['native_calls'] + r['hits']
        assert r['cached_dispatches'] == r['hits'] + r['misses']
        assert r['hit_resets'] <= r['hits'] and r['maximum_misses'] <= 64
        assert r['switches'] in [0, 1] and r['disabled'] == bool(r['switches'])
        if r['disabled']:
            assert r['maximum_misses'] == 64
            assert r['cached_dispatches'] == r['disabled_at_dispatch'] >= 64
        else:
            assert r['direct_dispatches'] == r['disabled_at_dispatch'] == 0
        misses = r['miss_run_hist']
        assert len(misses) == 65 and misses[0] == 0
        assert sum(i * n for i, n in enumerate(misses)) == r['misses']
        hist = r['vector_run_hist']
        assert len(hist) == 12 and r['vector_events'] == r['dispatches']
        assert sum(hist) == r['vector_changes'] + int(r['vector_events'] > 0)
        lower = [1, 2, 3, 4, 5, 9, 17, 33, 64, 65, 128, 256]
        upper = [1, 2, 3, 4, 8, 16, 32, 63, 64, 127, 255, r['vector_events']]
        assert sum(x * n for x, n in zip(lower, hist)) <= r['vector_events'] <= sum(x * n for x, n in zip(upper, hist))
        assert r['maximum_vector_run'] <= r['vector_events']
        assert r['equal_adjacent_after_disable'] <= r['direct_dispatches']
    return records


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--build', type=pathlib.Path, required=True)
    p.add_argument('--qualified', type=pathlib.Path, required=True)
    p.add_argument('--output', type=pathlib.Path, required=True)
    p.add_argument('--port', type=int, default=46710)
    a = p.parse_args()
    assert 1024 <= a.port <= 65520
    bc.nice10(); bc.child_limits()
    build = bc.checked_build(a.build)
    gate = json.loads((a.qualified / 'status.json').read_text())
    assert gate['status'] == 'PASS_DIAGNOSTIC_ORDINARY_SQL_NATIVE_BUDGET_FALLBACK'
    assert gate['remaining_owned'] == gate['timing_samples'] == 0 and not gate['cleanup_errors']
    assert gate['build_receipt_sha256'] == bc.sha(a.build / 'build-receipt.json')
    assert gate['budget_native_calls'] == 12936 and gate['budget_dispatch_transitions'] == 90
    assert set(gate['variants']) == {'DIAG'}
    artifact = gate['variants']['DIAG']
    assert bc.sha(artifact['path']) == artifact['sha256']
    assert json.loads(pathlib.Path(artifact['path']).read_text())['status'] == 'PASS'
    for key, expected in dict(ordered_cases_per_variant=40, prepared_cases_per_variant=7,
                              lifecycle_comparisons_per_variant=12, native_cases_per_variant=11,
                              budget_native_cases_per_variant=11, generic_fallback_cases_per_variant=11,
                              budget_initializations=132, budget_context_resets=22).items():
        assert gate[key] == expected
    assert bc.sha(HERE / 'source/SOURCE.json') == build['source_plan_sha256'] == '58b7e6177b1e5c2cfffe2893e7f93aeec027ef28d55890109b767a9211acc80d'
    for name, value in json.loads((a.qualified / 'frozen-inputs.json').read_text()).items():
        assert bc.sha(HERE / 'qualification' / name) == value['sha256']
    for item in gate['clusters']:
        assert item['stopped']
        bc.stopped(item['prefix'], item['data'])
        for key in ['pid', 'backend_pid']:
            assert not item.get(key) or not pathlib.Path('/proc', str(item[key])).exists()
    variants = build['variants']; variant = variants['DIAG']; prefix = pathlib.Path(variant['prefix'])
    out = a.output.resolve(); out.mkdir()
    state = dict(status='RUNNING_UNTIMED', pid=os.getpid(), started_ns=time.time_ns(),
                 build_receipt_sha256=bc.sha(a.build / 'build-receipt.json'),
                 qualification_sha256=bc.sha(a.qualified / 'status.json'),
                 timing_samples=0, captures={}, clusters=[], host_before=dict(load=list(os.getloadavg())))
    bc.save(out / 'status.json', state)
    cases = json.loads((HERE / 'diagnostic-source/CASES.json').read_text())
    assert len(cases['cases']) == 18 and cases['reports'] == 18
    reference = json.loads((HERE / 'qualification/reference-B-result.json').read_text())
    protocol = json.loads((HERE / 'diagnostic-source/SOURCE.json').read_text())
    assert variant['source_edited_files']['src/backend/access/gin/ginlogic.c'] == protocol['files']['src/backend/access/gin/ginlogic.c']
    seed = a.qualified / 'seed'; seed_inventory = json.loads((a.qualified / 'seed-inventory.json').read_text())
    assert bc.inventory(seed) == seed_inventory
    data = out / 'data'; shutil.copytree(seed, data); assert bc.inventory(data) == seed_inventory; bc.sync(data)
    frozen = {str(p.relative_to(HERE)): dict(bytes=p.stat().st_size, sha256=bc.sha(p))
              for p in [HERE / 'capture.py', HERE / 'diagnostic-source/gin-dispatch-diag.c', HERE / 'diagnostic-source/CASES.json']}
    bc.save(out / 'frozen-capture-inputs.json', frozen)
    s = None; cluster = None
    try:
        pg = prefix / 'bin/pg_config'
        flags = shlex.split(bc.capture([pg, '--cflags'], prefix)) + shlex.split(bc.capture([pg, '--cppflags'], prefix))
        headers = pathlib.Path(bc.capture([pg, '--includedir-server'], prefix).strip())
        assert bc.inventory(headers) == variant['headers']
        obj, module = out / 'gin-dispatch-diag.o', out / 'gin-dispatch-diag.so'
        bc.run(['gcc', *flags, '-Werror', '-fPIC', '-I' + str(headers), '-I' + str(prefix / 'include'),
                '-c', HERE / 'diagnostic-source/gin-dispatch-diag.c', '-o', obj], out / 'module-compile.log', prefix=prefix)
        bc.run(['gcc', '-shared', '-fno-lto', obj, '-o', module], out / 'module-link.log', prefix=prefix)
        bc.save(out / 'module.json', dict(module_sha256=bc.sha(module), source_sha256=bc.sha(HERE / 'diagnostic-source/gin-dispatch-diag.c'),
                                        headers_sha256=variant['headers_sha256'], flags=flags, postgres_sha256=variant['postgres_sha256']))
        socket = out.parent / 's/capture'; socket.parent.mkdir(exist_ok=True); socket = bc.socket_directory(socket, a.port)
        cluster = dict(prefix=str(prefix), data=str(data), socket=str(socket), port=a.port, stopped=False)
        state['clusters'].append(cluster); bc.save(out / 'status.json', state)
        options = f'-p {a.port} -k {socket} -c listen_addresses= -c shared_buffers=128MB -c autovacuum=off -c jit=off -c max_parallel_workers=0 -c max_parallel_workers_per_gather=0 -c huge_pages=off -c max_connections=8'
        bc.run([prefix / 'bin/pg_ctl', '-D', data, '-l', out / 'server.log', '-o', options, '-w', 'start'], out / 'start.log', prefix=prefix, timeout=120)
        cluster['pid'] = int((data / 'postmaster.pid').read_text().splitlines()[0])
        assert bc.sha(pathlib.Path('/proc', str(cluster['pid']), 'exe')) == variant['postgres_sha256']
        s = Session(prefix, bc.local_dsn(socket, a.port), out / 'psql-stderr.txt'); s.pid = int(s.sql('SELECT pg_backend_pid()')); cluster['backend_pid'] = s.pid
        assert bc.sha(pathlib.Path('/proc', str(s.pid), 'exe')) == variant['postgres_sha256']
        s.sql(cases['common_settings'])
        for name, signature in [('begin', '() RETURNS void'), ('finish', '() RETURNS text'), ('', '(regclass,tsquery,integer) RETURNS jsonb')]:
            suffix = '_' + name if name else ''
            s.sql('CREATE FUNCTION public.gin_dispatch_diag' + suffix + signature + " AS '" + str(module) + "','gin_dispatch_diag" + suffix + "' LANGUAGE C" + (' STRICT' if not name else ''))
        one_scan = {}
        with (out / 'raw.jsonl').open('x') as raw:
            for rank, case in enumerate(cases['cases']):
                state['phase'] = case['name']; bc.save(out / 'status.json', state)
                if case['kind'] == 'sql':
                    parent_name = case['name'].split('/')[1]; rows_sql = case['rows_sql']
                else:
                    parent_name = AM_REFERENCE[case['name'].split('/')[0]]
                    table = 'inline_docs' if parent_name == 'inline' else 'docs'
                    rows_sql = "SELECT id FROM g1." + table + " WHERE d @@ '" + case['query'] + "'::tsquery"
                ordered = 'SELECT id FROM (' + rows_sql + ') q ORDER BY id'
                s.sql(RESET + SEQ); ref = s.sql(ordered)
                s.sql(GIN); actual = s.sql(ordered)
                oracle = dict(reference=digest(ref), actual=digest(actual))
                bc.save(out / f'oracle-{rank:02}.json', oracle)
                assert ref == actual and oracle['actual'] == reference['rows'][parent_name]
                s.sql(RESET + cases['common_settings'] + (';' + case['settings'] if case['kind'] == 'sql' else ''))
                if case['kind'] == 'sql':
                    s.sql('SELECT public.gin_dispatch_diag_begin()')
                    answer = s.sql(case['sql'])
                    observed = s.sql('SELECT public.gin_dispatch_diag_finish()')
                    result = dict(probe=json.loads(observed))
                else:
                    command = "SELECT public.gin_dispatch_diag('" + case['index'] + "'::regclass,'" + case['query'] + "'::tsquery," + str(case['loops']) + ')'
                    observed = s.sql(command); answer = observed; result = json.loads(observed)
                row = dict(rank=rank, name=case['name'], kind=case['kind'], answer=answer, raw_capture=observed, result=result)
                # Full literal/counters are durable before scalar/count assertions.
                raw.write(json.dumps(row) + '\n'); raw.flush(); os.fsync(raw.fileno())
                bc.save(out / f'capture-{rank:02}.json', row)
                if case['kind'] == 'sql':
                    assert answer == case['answer']
                    expected_keys = 0 if parent_name == 'seq_control' else (10 if parent_name == 'dense_and' else 5 if parent_name in ['single_forced', 'or_forced'] else 100)
                    check_probe(result['probe'], expected_keys, case['expected_nuserentries'])
                else:
                    assert result['loops'] == case['loops'] and result['total_tids'] == case['total_tids']
                    records = check_probe(result['probe'], case['loops'], case['expected_nuserentries'])
                    summaries = [{k: v for k, v in item.items() if k != 'generation'} for item in records]
                    name = case['name'].split('/')[0]
                    if case['loops'] == 1: one_scan[name] = summaries[0]
                    assert all(value == one_scan[name] for value in summaries)
                state['captures'][case['name']] = dict(path=str(out / f'capture-{rank:02}.json'), sha256=bc.sha(out / f'capture-{rank:02}.json'))
        assert len(state['captures']) == 18
        bc.checked_build(a.build); assert bc.inventory(seed) == seed_inventory
        for name, value in frozen.items(): assert bc.sha(HERE / name) == value['sha256']
        state.update(status='PASS_EIGHTEEN_UNTIMED_DISPATCH_CAPTURES', raw_sha256=bc.sha(out / 'raw.jsonl'),
                     source_prefix_seed_inputs_unchanged=True, finished_ns=time.time_ns())
    except BaseException as exc:
        state.update(status='FAILED_PRESERVED_NO_RETRY', error=repr(exc), traceback=traceback.format_exc()); raise
    finally:
        errors = []
        if s:
            try: s.close(failed=state['status'] != 'PASS_EIGHTEEN_UNTIMED_DISPATCH_CAPTURES')
            except BaseException as exc: errors.append(dict(client=repr(exc)))
        if cluster:
            try:
                if (data / 'postmaster.pid').exists():
                    pid = int((data / 'postmaster.pid').read_text().splitlines()[0]); proc = pathlib.Path('/proc', str(pid))
                    assert proc.stat().st_uid == os.getuid() and bc.sha(proc / 'exe') == variant['postgres_sha256']
                    tokens = (proc / 'cmdline').read_bytes().split(b'\0'); assert str(data).encode() in tokens
                    bc.run([prefix / 'bin/pg_ctl', '-D', data, '-m', 'fast', '-w', 'stop'], out / 'stop.log', prefix=prefix, timeout=120)
                cluster.update(stopped=True, stop_proof=bc.stopped(prefix, data))
                assert not list(socket.glob('.s.PGSQL.*'))
                for key in ['pid', 'backend_pid']: assert not cluster.get(key) or not pathlib.Path('/proc', str(cluster[key])).exists()
            except BaseException as exc: errors.append(dict(cluster=repr(exc)))
        state.update(cleanup_errors=errors, remaining_owned=int(bool(cluster and not cluster.get('stopped'))))
        if errors or state['remaining_owned']: state['status'] = 'FAILED_CLEANUP'
        bc.save(out / 'status.json', state)
        if errors and not sys.exc_info()[0]: raise RuntimeError(errors)


if __name__ == '__main__':
    main()
