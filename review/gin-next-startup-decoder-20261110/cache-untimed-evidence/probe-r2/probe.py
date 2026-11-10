#!/usr/bin/env python3
"""Untimed actual-callback repetition counts on new own B/C9 fixture copies."""
import argparse
import gzip
import hashlib
import importlib.util
import json
import pathlib
import shlex
import shutil
import sys
import time
import traceback

HERE = pathlib.Path(__file__).resolve().parent
STARTUP = HERE.parent.parent / 'startup-decoder'
SEQ = 'SET enable_seqscan=on;SET enable_bitmapscan=off;SET enable_indexscan=off;SET enable_indexonlyscan=off;'
GIN = 'SET enable_seqscan=off;SET enable_bitmapscan=on;SET enable_indexscan=off;SET enable_indexonlyscan=off;'
CASES = [
    ('full', 'docs', 'common', 200000),
    ('or', 'docs', 'common | rare0', 200000),
    ('dense', 'docs', 'dense2 & dense3', 33333),
    ('rare', 'docs', 'rare0', 200),
    ('absent', 'docs', 'common & missing', 0),
    ('phrase', 'docs', 'common <-> rare0', 0),
    ('prefix', 'docs', 'group1:* & rare0', 53),
    ('not', 'docs', 'rare0 & !dense2', 0),
    ('not_positive', 'docs', 'rare1 & !dense2', 99),
    ('inline', 'inline', 'common & token17', 4),
    ('inline_single', 'inline', 'common', 256),
]


def digest(text):
    return dict(rows=len(text.splitlines()) if text else 0,
                sha256=hashlib.sha256(text.encode()).hexdigest())


def nodes(node):
    yield node
    for child in node.get('Plans', []):
        yield from nodes(child)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--build', type=pathlib.Path, required=True)
    p.add_argument('--qualified', type=pathlib.Path, required=True)
    p.add_argument('--output', type=pathlib.Path, required=True)
    p.add_argument('--first-port', type=int, default=45620)
    p.add_argument('--startup-root', type=pathlib.Path, default=STARTUP,
                   help='Source/build/qualification script root; explicit when staged separately')
    args = p.parse_args()
    startup = args.startup_root.resolve()
    sys.path.insert(0, str(startup / 'qualification'))
    from session import Session
    loader = importlib.util.spec_from_file_location('bc', startup / 'build-harness/common.py')
    bc = importlib.util.module_from_spec(loader)
    loader.loader.exec_module(bc)
    bc.nice10()
    build = bc.checked_build(args.build)
    qualification = json.loads((args.qualified / 'status.json').read_text())
    assert qualification['status'] == 'PASS_ORDINARY_SQL_AND_VALID_DECODER'
    assert qualification['remaining_owned'] == 0 and not qualification['cleanup_errors']
    assert qualification['build_receipt_sha256'] == bc.sha(args.build / 'build-receipt.json')
    out = args.output.resolve()
    out.mkdir()
    seed = args.qualified / 'seed'
    seed_inventory = json.loads((args.qualified / 'seed-inventory.json').read_text())
    assert bc.inventory(seed) == seed_inventory
    owned, sessions = [], []
    status = dict(status='RUNNING', timing_samples=0, cases={},
                  build_receipt_sha256=bc.sha(args.build / 'build-receipt.json'),
                  qualification_status_sha256=bc.sha(args.qualified / 'status.json'),
                  input_files={n: bc.sha(HERE / n) for n in ['probe.py', 'vector-probe.c', 'probe-setup.sql']})
    bc.save(out / 'status.json', status)

    def stop(item):
        if item.get('stopped'):
            return
        prefix, data = pathlib.Path(item['prefix']), pathlib.Path(item['data'])
        if (data / 'postmaster.pid').exists():
            bc.run([prefix / 'bin/pg_ctl', '-D', data, '-m', 'fast', '-w', 'stop'],
                   out / (item['role'] + '-stop.log'), prefix=prefix, timeout=120)
        item['stop_proof'] = bc.stopped(prefix, data)
        assert not pathlib.Path(item['socket'], '.s.PGSQL.' + str(item['port'])).exists()
        for name in ('pid', 'backend_pid'):
            assert not item.get(name) or not pathlib.Path('/proc', str(item[name])).exists()
        item['stopped'] = True

    try:
        for index, role in enumerate(['B', 'C9']):
            v = build['variants'][role]
            prefix = pathlib.Path(v['prefix'])
            stage = out / role
            stage.mkdir()
            pg = prefix / 'bin/pg_config'
            flags = shlex.split(bc.capture([pg, '--cflags'], prefix)) + shlex.split(bc.capture([pg, '--cppflags'], prefix))
            headers = pathlib.Path(bc.capture([pg, '--includedir-server'], prefix).strip())
            assert bc.inventory(headers) == v['headers']
            obj, module = stage / 'probe.o', stage / 'probe.so'
            bc.run(['gcc', *flags, '-Werror', '-fPIC', '-I' + str(headers), '-I' + str(prefix / 'include'),
                    '-c', HERE / 'vector-probe.c', '-o', obj], stage / 'compile.log', prefix=prefix)
            bc.run(['gcc', '-shared', '-fno-lto', obj, '-o', module], stage / 'link.log', prefix=prefix)
            data = out / ('data-' + role)
            shutil.copytree(seed, data)
            assert bc.inventory(data) == seed_inventory
            port = args.first_port + index
            socket = bc.socket_directory(out / ('s-' + role), port)
            item = dict(role=role, data=str(data), prefix=str(prefix), port=port, socket=str(socket))
            owned.append(item)
            bc.save(out / 'owned.json', owned)
            opts = (f'-p {port} -k {socket} -c listen_addresses= -c shared_buffers=128MB '
                    '-c max_parallel_workers=0 -c max_parallel_workers_per_gather=0 -c autovacuum=off '
                    '-c jit=off -c max_connections=8 -c huge_pages=off -c timing_clock_source=system')
            bc.run([prefix / 'bin/pg_ctl', '-D', data, '-l', stage / 'server.log', '-o', opts, '-w', 'start'],
                   stage / 'start.log', prefix=prefix, timeout=120)
            item['pid'] = int((data / 'postmaster.pid').read_text().splitlines()[0])
            s = Session(prefix, bc.local_dsn(socket, port), stage / 'psql-stderr.txt')
            sessions.append(s)
            item['backend_pid'] = int(s.sql('SELECT pg_backend_pid()'))
            assert bc.sha(pathlib.Path('/proc', str(item['backend_pid']), 'exe')) == v['postgres_sha256']
            try:
                s.sql("SET search_path=cache_probe,g1,public,pg_catalog;SET jit=off;SET enable_memoize=off;SET gin_fuzzy_search_limit=0;SET statement_timeout='180s';SET lock_timeout='10s';SET work_mem='64MB'")
                template = (HERE / 'probe-setup.sql').read_text().replace(":'MODULE'", "'" + str(module).replace("'", "''") + "'")
                s.sql(template)
                s.sql('CREATE TABLE cache_probe.inline AS SELECT id,d FROM g1.inline_docs;CREATE INDEX probe_inline_gin ON cache_probe.inline USING gin(d cache_probe.probe_ops) WITH(fastupdate=off);VACUUM(FREEZE,ANALYZE) cache_probe.inline')
                status['cases'][role] = {}
                for name, table, query, expected in CASES:
                    original = 'g1.inline_docs' if table == 'inline' else 'g1.docs'
                    condition = " WHERE d @@ '" + query + "'::tsquery ORDER BY id"
                    s.sql(SEQ)
                    reference = s.sql('SELECT id FROM ' + original + condition)
                    s.sql(GIN)
                    original_gin = s.sql('SELECT id FROM ' + original + condition)
                    s.sql('SELECT cache_probe.reset()')
                    actual = s.sql('SELECT id FROM cache_probe.' + table + condition)
                    raw_counts = s.sql('SELECT cache_probe.report()')
                    (stage / (name + '-counts.txt')).write_text(raw_counts + '\n')
                    plan = s.json('EXPLAIN(FORMAT JSON) SELECT id FROM cache_probe.' + table + condition)[0]['Plan']
                    result = dict(reference=digest(reference), original_gin=digest(original_gin), actual=digest(actual),
                                  literal_count=str(expected), observed_counts=json.loads(raw_counts), plan=plan)
                    bc.save(stage / (name + '.json'), result)
                    (stage / (name + '-reference.txt.gz')).write_bytes(gzip.compress(reference.encode(), mtime=0))
                    assert actual == original_gin == reference
                    assert result['actual']['rows'] == expected
                    assert any(n.get('Index Name') == ('probe_inline_gin' if table == 'inline' else 'probe_d_gin') for n in nodes(plan))
                    for counts in result['observed_counts']['callbacks'].values():
                        assert counts['false'] + counts['true'] + counts['maybe'] == counts['calls']
                        assert 0 <= counts['consecutive_same_vector'] <= counts['eligible'] <= counts['calls']
                    status['cases'][role][name] = dict(path=str(stage / (name + '.json')), sha256=bc.sha(stage / (name + '.json')))
                    bc.save(out / 'status.json', status)
                status[role + '_module'] = dict(sha256=bc.sha(module), source_sha256=bc.sha(HERE / 'vector-probe.c'), headers_sha256=v['headers_sha256'])
            finally:
                s.close(failed=sys.exc_info()[0] is not None)
                stop(item)
            bc.save(out / 'owned.json', owned)
        assert bc.inventory(seed) == seed_inventory
        bc.checked_build(args.build)
        for name, sha256 in status['input_files'].items():
            assert bc.sha(HERE / name) == sha256
        status.update(status='PASS_UNTIMED_CALLBACK_REPETITION', timing_samples=0, finished_ns=time.time_ns())
    except BaseException as exc:
        status.update(status='FAILED_PRESERVED', error=repr(exc), traceback=traceback.format_exc())
        raise
    finally:
        errors = []
        for s in reversed(sessions):
            try:
                s.close(failed=True)
            except BaseException as exc:
                errors.append(dict(client_pid=s.proc.pid, error=repr(exc)))
        for item in reversed(owned):
            try:
                stop(item)
            except BaseException as exc:
                errors.append(dict(role=item['role'], error=repr(exc)))
        status.update(cleanup_errors=errors, remaining_owned=sum(not x.get('stopped', False) for x in owned))
        if errors or status['remaining_owned']:
            status['status'] = 'FAILED_CLEANUP'
        bc.save(out / 'status.json', status)
        bc.save(out / 'owned.json', owned)
        if errors and not sys.exc_info()[0]:
            raise RuntimeError(errors)


if __name__ == '__main__':
    main()
