#!/usr/bin/env python3
"""Compile exact cache production TU and exercise it with real PG metadata, untimed."""
import argparse
import importlib.util
import json
import pathlib
import shlex
import shutil
import sys
import traceback

HERE = pathlib.Path(__file__).resolve().parent
QUERIES = [
    ('one', 'common', 1, False),
    ('or2', 'common | rare0', 2, False),
    ('dense2', 'dense2 & dense3', 2, False),
    ('phrase2', 'common <-> rare0', 2, False),
    ('weighted2', 'common:A & rare0', 2, False),
    ('prefix2', 'group1:* & rare0', 2, False),
    ('not2', 'rare1 & !dense2', 2, False),
    ('eight', 'a | b | c | d | e | f | g | h', 8, False),
    ('nine', 'a | b | c | d | e | f | g | h | i', 9, False),
    ('hidden9', 'a | b | c | d | e | f | g | h', 8, True),
    ('hidden2', '!missing', 1, True),
]


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--startup-root', type=pathlib.Path, required=True)
    p.add_argument('--build', type=pathlib.Path, required=True)
    p.add_argument('--qualified', type=pathlib.Path, required=True)
    p.add_argument('--output', type=pathlib.Path, required=True)
    p.add_argument('--first-port', type=int, default=45630)
    args = p.parse_args()
    sys.path.insert(0, str(args.startup_root / 'qualification'))
    from session import Session
    loader = importlib.util.spec_from_file_location('bc', args.startup_root / 'build-harness/common.py')
    bc = importlib.util.module_from_spec(loader)
    loader.loader.exec_module(bc)
    bc.nice10()
    build = bc.checked_build(args.build)
    q = json.loads((args.qualified / 'status.json').read_text())
    assert q['status'] == 'PASS_ORDINARY_SQL_AND_VALID_DECODER' and q['remaining_owned'] == 0 and not q['cleanup_errors']
    assert q['build_receipt_sha256'] == bc.sha(args.build / 'build-receipt.json')
    out = args.output.resolve()
    out.mkdir()
    seed = args.qualified / 'seed'
    expected_seed = json.loads((args.qualified / 'seed-inventory.json').read_text())
    assert bc.inventory(seed) == expected_seed
    frozen = {p.relative_to(HERE).as_posix(): dict(bytes=p.stat().st_size, sha256=bc.sha(p))
              for p in HERE.rglob('*') if p.is_file() and '__pycache__' not in p.parts}
    state = dict(status='RUNNING', timing_samples=0, units=[], native={}, clusters=[],
                 scope='Actual-header production-TU/native prototype only; K1 full backend and SQL are NOTRUN',
                 build_receipt_sha256=bc.sha(args.build / 'build-receipt.json'), inputs=frozen)
    bc.save(out / 'status.json', state)
    sessions, owned = [], []

    def stop(item):
        if item.get('stopped'):
            return
        prefix, data = pathlib.Path(item['prefix']), pathlib.Path(item['data'])
        if (data / 'postmaster.pid').exists():
            bc.run([prefix / 'bin/pg_ctl', '-D', data, '-m', 'fast', '-w', 'stop'],
                   out / (item['label'] + '-stop.log'), prefix=prefix, timeout=120)
        item['stop_proof'] = bc.stopped(prefix, data)
        for key in ['pid', 'backend_pid']:
            assert not item.get(key) or not pathlib.Path('/proc', str(item[key])).exists()
        assert not pathlib.Path(item['socket'], '.s.PGSQL.' + str(item['port'])).exists()
        item['stopped'] = True

    try:
        for index, (label, reference) in enumerate([('normal', 'B'), ('assert', 'S1_assert')]):
            v = build['variants'][reference]
            prefix = pathlib.Path(v['prefix'])
            stage = out / label
            stage.mkdir()
            pg = prefix / 'bin/pg_config'
            flags = shlex.split(bc.capture([pg, '--cflags'], prefix)) + shlex.split(bc.capture([pg, '--cppflags'], prefix))
            headers = pathlib.Path(bc.capture([pg, '--includedir-server'], prefix).strip())
            assert bc.inventory(headers) == v['headers']
            include = ['-I' + str(HERE / 'production'), '-I' + str(headers), '-I' + str(prefix / 'include')]
            for stem in ['ginlogic', 'ginget', 'ginscan']:
                source = HERE / 'production' / (stem + '.c')
                obj = stage / (stem + '.o')
                rename = ['-DginInitConsistentFunction=gin_cache_init_prototype'] if stem == 'ginlogic' else []
                bc.run(['gcc', *flags, '-Werror', '-fPIC', *include, *rename, '-c', source, '-o', obj],
                       stage / (stem + '-compile.log'), prefix=prefix)
                state['units'].append(dict(mode=label, stem=stem, source_sha256=bc.sha(source),
                    object_sha256=bc.sha(obj), real_headers_sha256=v['headers_sha256'],
                    overlay_header_sha256=bc.sha(HERE / 'production/access/gin_private.h'), production_flags=flags, renamed_entry_symbol=bool(rename)))
            bc.run(['objdump', '-drwC', stage / 'ginlogic.o'], stage / 'ginlogic-ASM.txt')
            obj, module = stage / 'native-oracle.o', stage / 'native-oracle.so'
            bc.run(['gcc', *flags, '-Werror', '-fPIC', *include, '-c', HERE / 'native-oracle.c', '-o', obj],
                   stage / 'native-compile.log', prefix=prefix)
            bc.run(['gcc', '-shared', '-fno-lto', obj, stage / 'ginlogic.o', '-o', module],
                   stage / 'native-link.log', prefix=prefix)
            data = out / ('data-' + label)
            shutil.copytree(seed, data)
            assert bc.inventory(data) == expected_seed
            bc.sync(data)
            port = args.first_port + index
            socket = bc.socket_directory(out / ('s-' + label), port)
            item = dict(label=label, data=str(data), prefix=str(prefix), port=port, socket=str(socket))
            owned.append(item); state['clusters'].append(item)
            bc.save(out / 'status.json', state)
            opts = (f'-p {port} -k {socket} -c listen_addresses= -c shared_buffers=128MB -c jit=off '
                    '-c autovacuum=off -c max_parallel_workers=0 -c max_parallel_workers_per_gather=0 '
                    '-c max_connections=8 -c huge_pages=off -c timing_clock_source=system')
            bc.run([prefix / 'bin/pg_ctl', '-D', data, '-l', stage / 'server.log', '-o', opts, '-w', 'start'],
                   stage / 'start.log', prefix=prefix, timeout=120)
            item['pid'] = int((data / 'postmaster.pid').read_text().splitlines()[0])
            s = Session(prefix, bc.local_dsn(socket, port), stage / 'psql-stderr.txt')
            sessions.append(s)
            item['backend_pid'] = int(s.sql('SELECT pg_backend_pid()'))
            assert bc.sha(pathlib.Path('/proc', str(item['backend_pid']), 'exe')) == v['postgres_sha256']
            try:
                assert (s.sql('SHOW debug_assertions') == 'on') == (label == 'assert')
                s.sql("SET statement_timeout='120s';SET lock_timeout='10s';CREATE FUNCTION public.gin_cache_native_oracle(regclass,tsquery,boolean) RETURNS text AS '" + str(module) + "', 'gin_cache_native_oracle' LANGUAGE C STRICT")
                state['native'][label] = {}
                for name, query, n, hidden in QUERIES:
                    raw = s.sql("SELECT public.gin_cache_native_oracle('g1.docs_d_gin'::regclass,'" + query + "'::tsquery," + str(hidden).lower() + ')')
                    path = stage / (name + '-raw.txt')
                    path.write_text(raw + '\n')
                    with path.open('rb') as f:
                        import os
                        os.fsync(f.fileno())
                    value = json.loads(raw)
                    state['native'][label][name] = value
                    bc.save(out / 'status.json', state)
                    entries = n + int(hidden)
                    assert value == dict(status='PASS_VALID_NATIVE_TRI_MEMO', nuserentries=n, nentries=entries,
                                         cache_allocated=n <= 8, vectors=3 ** entries, checks=4 * 3 ** entries, timing_samples=0)
            finally:
                s.close(failed=sys.exc_info()[0] is not None)
                stop(item)
            state[label + '_module'] = dict(sha256=bc.sha(module), headers_sha256=v['headers_sha256'])
        bc.checked_build(args.build)
        assert bc.inventory(seed) == expected_seed
        for n, v in frozen.items():
            assert (HERE / n).stat().st_size == v['bytes'] and bc.sha(HERE / n) == v['sha256']
        state.update(status='PASS_ACTUAL_HEADER_NATIVE_PROTOTYPE', production_units=6,
                     native_vectors=sum(x['vectors'] for mode in state['native'].values() for x in mode.values()),
                     native_checks=sum(x['checks'] for mode in state['native'].values() for x in mode.values()))
    except BaseException as exc:
        state.update(status='FAILED_PRESERVED', error=repr(exc), traceback=traceback.format_exc())
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
                errors.append(dict(label=item['label'], error=repr(exc)))
        state.update(cleanup_errors=errors, remaining_owned=sum(not x.get('stopped', False) for x in owned))
        if errors or state['remaining_owned']:
            state['status'] = 'FAILED_CLEANUP'
        bc.save(out / 'status.json', state)
        if errors and not sys.exc_info()[0]:
            raise RuntimeError(errors)


if __name__ == '__main__':
    main()
