#!/usr/bin/env python3
"""Finite ordinary SQL and actual-decoder qualification; no performance samples."""
import argparse
import gzip
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
from session import Session
from mixed_expected import reference as mixed_integer_reference

HERE = pathlib.Path(__file__).resolve().parent
loader = importlib.util.spec_from_file_location('bc', HERE.parent / 'build-harness/common.py')
bc = importlib.util.module_from_spec(loader)
loader.loader.exec_module(bc)
VARIANTS = ('B', 'D2', 'D3', 'D3_assert')
SEQ = 'SET enable_seqscan=on;SET enable_bitmapscan=off;SET enable_indexscan=off;SET enable_indexonlyscan=off;'
GIN = 'SET enable_seqscan=off;SET enable_bitmapscan=on;SET enable_indexscan=off;SET enable_indexonlyscan=off;'
RESET = "RESET enable_seqscan;RESET enable_bitmapscan;RESET enable_indexscan;RESET enable_indexonlyscan;SET work_mem='64MB';"
SETTINGS = ("SET search_path=g1,public,pg_catalog;SET jit=off;SET max_parallel_workers_per_gather=0;"
            "SET enable_memoize=off;SET gin_fuzzy_search_limit=0;SET statement_timeout='180s';"
            "SET lock_timeout='10s';SET work_mem='64MB';")


def digest(value):
    data = value.encode()
    return dict(bytes=len(data), rows=len(value.splitlines()) if value else 0,
                sha256=hashlib.sha256(data).hexdigest())


def nodes(node):
    yield node
    for child in node.get('Plans', []):
        yield from nodes(child)


def extra_cases():
    # Independent literals derive directly from the frozen 200000-row recipe.
    ft = [
        ('absent_reverse', 'missing & common', 0),
        ('absent_nested', '(common | dense2) & missing', 0),
        ('absent_or', 'common | missing', 200000),
        ('missing_only', 'missing', 0),
        ('absent_phrase', 'common <-> missing', 0),
        ('absent_prefix_fallback', 'group1:* & missing', 0),
        ('absent_not_positive', 'common & !missing', 200000),
        ('absent_duplicate', 'common & common & missing', 0),
        ('empty_query', '', 0),
    ]
    result = [dict(name=n, rows_sql="SELECT id FROM g1.docs WHERE d @@ '" + q + "'::tsquery",
                   answer=str(count), index='docs_d_gin') for n, q, count in ft]
    for name, table, predicate, index, count in [
        ('separate_absent', 'docs', "d @@ 'common'::tsquery AND d @@ 'missing'::tsquery", 'docs_d_gin', 0),
        ('inline_absent', 'inline_docs', "d @@ 'common & missing'::tsquery", 'inline_d_gin', 0),
        ('intarray_absent', 'docs', 'tags @> ARRAY[1,99999999]', 'docs_tags_gin', 0),
        ('array_absent', 'builtin_arrays', 'tags OPERATOR(pg_catalog.@>) ARRAY[1,99999999]', 'builtin_tags_gin', 0),
        ('array_null_category', 'builtin_arrays', 'tags OPERATOR(pg_catalog.@>) ARRAY[NULL]::int[]', 'builtin_tags_gin', 0),
        ('jsonb_absent', 'docs', "jb @> '{\"common\":true,\"missing\":42}'::jsonb", 'docs_jb_gin', 0),
    ]:
        result.append(dict(name=name, rows_sql='SELECT id FROM g1.' + table + ' WHERE ' + predicate,
                           answer=str(count), index=index))
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--build', required=True, type=pathlib.Path)
    parser.add_argument('--output', required=True, type=pathlib.Path,
                        help='New path only; preserve every failed attempt')
    parser.add_argument('--first-port', type=int, default=48160)
    args = parser.parse_args()
    assert 1024 <= args.first_port <= 65520
    out = args.output.resolve()
    out.mkdir()
    bc.nice10()
    bc.child_limits()
    receipt = bc.checked_build(args.build)
    prefixes = {k: pathlib.Path(v['prefix']) for k, v in receipt['variants'].items()}
    state = dict(status='RUNNING', phase='seed', pid=os.getpid(), started_ns=time.time_ns(),
                 timing_samples=0, build_receipt_sha256=bc.sha(args.build / 'build-receipt.json'),
                 source_plan_sha256=receipt['source_plan_sha256'], variants={}, clusters=[],
                 host_before=dict(load=os.getloadavg(), affinity=sorted(os.sched_getaffinity(0))))
    bc.save(out / 'status.json', state)
    frozen = {p.relative_to(HERE).as_posix(): dict(bytes=p.stat().st_size, sha256=bc.sha(p))
              for p in sorted(HERE.rglob('*')) if p.is_file() and '__pycache__' not in p.parts}
    bc.save(out / 'frozen-inputs.json', frozen)
    cases = (json.loads((HERE / 'inputs/queries.json').read_text())['cases'] +
             json.loads((HERE / 'inputs/queries-holdout.json').read_text())['cases'])
    answers = json.loads((HERE / 'inputs/answers.json').read_text())
    assert len(cases) == 25 and len(extra_cases()) == 15
    owned, sessions = [], []

    def start(label, variant, data, port):
        prefix = prefixes[variant]
        (out.parent / 's').mkdir(exist_ok=True)
        sock = bc.socket_directory(out.parent / 's' / ('q-' + label), port)
        item = dict(label=label, variant=variant, prefix=str(prefix), data=str(data), socket=str(sock), port=port)
        owned.append(item)
        state['clusters'].append(item)
        bc.save(out / 'status.json', state)
        opts = (f'-p {port} -k {sock} -c listen_addresses= -c shared_buffers=128MB '
                '-c autovacuum=off -c jit=off -c max_parallel_workers_per_gather=0 '
                '-c max_parallel_workers=0 -c max_connections=8 -c huge_pages=off '
                '-c timing_clock_source=system -c checkpoint_timeout=1h -c max_wal_size=1GB')
        bc.run([prefix / 'bin/pg_ctl', '-D', data, '-l', out / (label + '-server.log'),
                '-o', opts, '-w', 'start'], out / (label + '-start.log'), prefix=prefix, timeout=120)
        item['pid'] = int((data / 'postmaster.pid').read_text().splitlines()[0])
        assert bc.sha(pathlib.Path('/proc', str(item['pid']), 'exe')) == receipt['variants'][variant]['postgres_sha256']
        s = Session(prefix, bc.local_dsn(sock, port), out / (label + '-psql-stderr.txt'))
        sessions.append(s)
        s.pid = int(s.sql('SELECT pg_backend_pid()'))
        item['backend_pid'] = s.pid
        s.sql(SETTINGS)
        bc.save(out / 'status.json', state)
        return item, s

    def stop(item):
        if item.get('stopped'):
            return
        data, prefix = pathlib.Path(item['data']), pathlib.Path(item['prefix'])
        assert data.parent == out
        if (data / 'postmaster.pid').exists():
            pid = int((data / 'postmaster.pid').read_text().splitlines()[0])
            assert not item.get('pid') or item['pid'] == pid
            proc = pathlib.Path('/proc', str(pid))
            if proc.exists():
                assert proc.stat().st_uid == os.getuid()
                assert bc.sha(proc / 'exe') == receipt['variants'][item['variant']]['postgres_sha256']
                tokens = (proc / 'cmdline').read_bytes().split(b'\0')
                assert b'-D' in tokens
                assert pathlib.Path(os.fsdecode(tokens[tokens.index(b'-D') + 1])).resolve() == data.resolve()
                bc.run([prefix / 'bin/pg_ctl', '-D', data, '-m', 'fast', '-w', 'stop'],
                       out / (item['label'] + '-stop.log'), prefix=prefix, timeout=120)
        proof = bc.stopped(prefix, data)
        assert not pathlib.Path(item['socket'], '.s.PGSQL.' + str(item['port'])).exists()
        for key in ('pid', 'backend_pid'):
            assert not item.get(key) or not pathlib.Path('/proc', str(item[key])).exists()
        item.update(stopped=True, stop_proof=proof)
        bc.save(out / 'status.json', state)

    def row_comparison(s, variant, name, rows_sql, intended_index=None, allow_fold=False):
        query = 'SELECT id FROM (' + rows_sql + ') q ORDER BY id'
        s.sql(RESET + SEQ)
        reference = s.sql(query)
        seq_plan = s.json('EXPLAIN(FORMAT JSON) ' + query)[0]['Plan']
        s.sql(GIN)
        actual = s.sql(query)
        gin_plan = s.json('EXPLAIN(FORMAT JSON) ' + query)[0]['Plan']
        result = dict(reference=digest(reference), actual=digest(actual), seq_plan=seq_plan, gin_plan=gin_plan)
        # Durable evidence precedes acceptance assertions.
        bc.save(out / (variant + '-' + name + '.json'), result)
        if variant == 'B':
            (out / ('reference-' + name + '.txt.gz')).write_bytes(gzip.compress(reference.encode(), mtime=0))
        if reference != actual:
            (out / (variant + '-' + name + '-actual.txt.gz')).write_bytes(gzip.compress(actual.encode(), mtime=0))
        assert reference == actual, (variant, name, 'ordered Seq/GIN multiset')
        folded = allow_fold and all(n['Node Type'] != 'Seq Scan' for n in nodes(seq_plan))
        if not folded:
            assert any(n['Node Type'] == 'Seq Scan' for n in nodes(seq_plan)), (name, 'forced Seq path')
        if intended_index and not (allow_fold and not any('Index Name' in n for n in nodes(gin_plan))):
            assert any(n.get('Index Name') == intended_index for n in nodes(gin_plan)), (name, 'forced GIN path')
        return result

    try:
        seed = out / 'seed'
        bc.run([prefixes['B'] / 'bin/initdb', '-D', seed, '--no-locale', '--encoding=UTF8',
                '--auth=trust', '--data-checksums'], out / 'seed-initdb.log', prefix=prefixes['B'])
        seed_item, s = start('seed', 'B', seed, args.first_port)
        try:
            s.sql((HERE / 'inputs/setup.sql').read_text())
            assert s.sql('SELECT count(*) FROM g1.docs') == '200002'
            s.sql('CHECKPOINT')
        finally:
            s.close(failed=sys.exc_info()[0] is not None)
            stop(seed_item)
        seed_inventory = bc.inventory(seed)
        bc.save(out / 'seed-inventory.json', seed_inventory)
        prior_reference = json.loads((HERE / 'reference-B.json').read_text())
        baseline_rows, baseline_decoder = prior_reference['rows'], prior_reference['decoder']
        mixed_reference = json.loads((HERE / 'mixed-reference.json').read_text())
        assert mixed_reference == mixed_integer_reference()
        for ix, variant in enumerate(VARIANTS):
            state['phase'] = variant
            bc.save(out / 'status.json', state)
            prefix = prefixes[variant]
            stage = out / variant
            stage.mkdir()
            pg = prefix / 'bin/pg_config'
            flags = shlex.split(bc.capture([pg, '--cflags'], prefix)) + shlex.split(bc.capture([pg, '--cppflags'], prefix))
            headers = pathlib.Path(bc.capture([pg, '--includedir-server'], prefix).strip())
            assert bc.inventory(headers) == receipt['variants'][variant]['headers']
            obj, module = stage / 'decoder-native.o', stage / 'decoder-native.so'
            bc.run(['gcc', *flags, '-Werror', '-fPIC', '-I' + str(headers), '-I' + str(prefix / 'include'),
                    '-c', HERE / 'decoder-native.c', '-o', obj], stage / 'compile.log', prefix=prefix)
            bc.run(['gcc', '-shared', '-fno-lto', obj, '-o', module], stage / 'link.log', prefix=prefix)
            data = out / ('data-' + variant)
            shutil.copytree(seed, data)
            assert bc.inventory(data) == seed_inventory
            bc.sync(data)
            item, s = start(variant, variant, data, args.first_port + 1 + ix)
            result = dict(status='RUNNING', cases={}, extra_cases={}, prepared={}, lifecycle={},
                          source_commit=receipt['variants'][variant]['commit'],
                          postgres_sha256=receipt['variants'][variant]['postgres_sha256'],
                          module_sha256=bc.sha(module), module_source_sha256=bc.sha(HERE / 'decoder-native.c'),
                          production_flags=flags, headers_sha256=receipt['variants'][variant]['headers_sha256'])
            try:
                assert (s.sql('SHOW debug_assertions') == 'on') == variant.endswith('_assert')
                s.sql("CREATE FUNCTION public.gin_decoder_oracle() RETURNS text AS '" + str(module) + "', 'gin_decoder_oracle' LANGUAGE C STRICT")
                raw = s.sql('SELECT public.gin_decoder_oracle()')
                with (stage / 'decoder-raw.txt').open('x') as stream:
                    stream.write(raw + '\n'); stream.flush(); os.fsync(stream.fileno())
                decoder = json.loads(raw)
                result['decoder'] = decoder
                bc.save(stage / 'result.json', result)
                assert decoder['status'] == 'PASS_VALID_DECODER' and decoder['timing_samples'] == 0
                assert len(decoder['cases']) == 21
                legacy = dict(decoder, cases=decoder['cases'][:18], checked_items=sum(c['items'] for c in decoder['cases'][:18]))
                assert legacy == baseline_decoder
                assert decoder['cases'][18:] == mixed_reference['decoder_extra']
                assert decoder['checked_items'] == 13536
                s.sql("CREATE FUNCTION public.gin_decoder_boundaries() RETURNS text AS '" + str(module) + "', 'gin_decoder_boundaries' LANGUAGE C STRICT")
                raw_boundaries = s.sql('SELECT public.gin_decoder_boundaries()')
                with (stage / 'boundary-raw.txt').open('x') as stream:
                    stream.write(raw_boundaries + '\n'); stream.flush(); os.fsync(stream.fileno())
                result['mixed_boundaries'] = json.loads(raw_boundaries)
                bc.save(stage / 'result.json', result)
                assert result['mixed_boundaries'] == mixed_reference['boundaries']
                result['decoder'] = decoder
                for case in cases:
                    value = row_comparison(s, variant, case['name'], case['rows_sql'], case['index'])
                    assert value['actual'] == baseline_rows[case['name']]
                    s.sql(RESET + case['settings'])
                    literal = s.sql(case['sql'])
                    plan = s.json('EXPLAIN(FORMAT JSON) ' + case['sql'])[0]['Plan']
                    indexes = [n['Index Name'] for n in nodes(plan) if 'Index Name' in n]
                    result['cases'][case['name']] = dict(literal=literal, plan=plan, multiset=value['actual'])
                    bc.save(stage / 'result.json', result)
                    assert literal == answers[case['name']]
                    assert (case['index'] in indexes) if case['index'] else not indexes
                for case in extra_cases():
                    value = row_comparison(s, variant, case['name'], case['rows_sql'], case['index'],
                                           allow_fold=case['name'] == 'empty_query')
                    s.sql(RESET + GIN)
                    count = s.sql('SELECT count(*) FROM (' + case['rows_sql'] + ') q')
                    result['extra_cases'][case['name']] = dict(count=count, **value)
                    bc.save(stage / 'result.json', result)
                    assert count == case['answer']
                    assert value['actual'] == baseline_rows[case['name']]
                s.sql(RESET + 'SET plan_cache_mode=force_generic_plan;PREPARE repeated_gin(tsquery) AS SELECT id FROM g1.docs WHERE d @@ $1 ORDER BY id')
                for text in ['common & missing', 'common | missing', 'common & rare0', 'dense2 & dense3', 'common', 'group1:* & missing', 'common <-> rare0']:
                    query = "EXECUTE repeated_gin('" + text + "'::tsquery)"
                    s.sql(SEQ + 'DISCARD PLANS')
                    reference = s.sql(query)
                    seq_plan = s.json('EXPLAIN(FORMAT JSON) ' + query)[0]['Plan']
                    s.sql(GIN + 'DISCARD PLANS')
                    actual = s.sql(query)
                    repeated = s.sql(query)
                    gin_plan = s.json('EXPLAIN(FORMAT JSON) ' + query)[0]['Plan']
                    result['prepared'][text] = dict(reference=digest(reference), actual=digest(actual), repeated=digest(repeated),
                                                   seq_plan=seq_plan, gin_plan=gin_plan)
                    bc.save(stage / 'result.json', result)
                    assert reference == actual == repeated
                    assert any(n['Node Type'] == 'Seq Scan' for n in nodes(seq_plan))
                    assert any(n.get('Index Name') == 'docs_d_gin' for n in nodes(gin_plan))
                    assert digest(actual) == baseline_rows['prepared-' + text]
                s.sql('DEALLOCATE repeated_gin')
                # Ordinary one-session pending-list writes; no concurrent actors.
                for phase, mutation in [
                    ('initial', ''),
                    ('insert', "INSERT INTO g1.writes SELECT 200000+g,to_tsvector('simple','common missing'),ARRAY[1,99999999],'{\"common\":true,\"missing\":42}'::jsonb FROM generate_series(1,32) g"),
                    ('delete', 'DELETE FROM g1.writes WHERE id > 200000'),
                    ('vacuum', 'VACUUM(ANALYZE) g1.writes'),
                ]:
                    if mutation:
                        s.sql(mutation)
                    result['lifecycle'][phase] = {}
                    for text in ['common & missing', 'common | missing', 'common & rare0']:
                        value = row_comparison(s, variant, 'writes-' + phase + '-' + text.replace(' ', '').replace('&', 'and').replace('|', 'or'),
                                               "SELECT id FROM g1.writes WHERE d @@ '" + text + "'::tsquery", 'writes_d_gin')
                        result['lifecycle'][phase][text] = value['actual']
                        assert value['actual'] == prior_reference['lifecycle'][phase][text]
                    bc.save(stage / 'result.json', result)
                s.sql('BEGIN ISOLATION LEVEL SERIALIZABLE READ ONLY')
                for text in ['common & missing', 'common & rare0', 'common | missing']:
                    s.sql("SELECT count(*) FROM g1.docs WHERE d @@ '" + text + "'::tsquery")
                s.sql('COMMIT')
                result.update(status='PASS', timing_samples=0)
                bc.save(stage / 'result.json', result)
                state['variants'][variant] = dict(path=str(stage / 'result.json'), sha256=bc.sha(stage / 'result.json'))
            finally:
                s.close(failed=sys.exc_info()[0] is not None)
                stop(item)
            assert bc.inventory(seed) == seed_inventory
        bc.checked_build(args.build)
        for name, value in frozen.items():
            assert (HERE / name).stat().st_size == value['bytes'] and bc.sha(HERE / name) == value['sha256']
        state.update(status='PASS_D3_ORDINARY_SQL_AND_VALID_DECODER', timing_samples=0,
                     ordered_cases_per_variant=40, prepared_cases_per_variant=7,
                     lifecycle_comparisons_per_variant=12, decoder_cases_per_variant=21, mixed_boundary_cases_per_variant=192,
                     mixed_boundary_item_checks_per_variant=8352,
                     seed_unchanged=True, installed_trees_unchanged=True, frozen_inputs_unchanged=True,
                     host_after=dict(load=os.getloadavg()), finished_ns=time.time_ns())
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
                errors.append(dict(cluster=item['label'], error=repr(exc)))
        state['cleanup_errors'] = errors
        state['remaining_owned'] = sum(not x.get('stopped', False) for x in owned)
        if errors or state['remaining_owned']:
            state['status'] = 'FAILED_CLEANUP'
        bc.save(out / 'status.json', state)
        if errors and not sys.exc_info()[0]:
            raise RuntimeError(errors)


if __name__ == '__main__':
    main()
