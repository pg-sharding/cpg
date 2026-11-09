#!/usr/bin/env python3
"""Untimed leaf/internal locked-page oracle in a new, owned assert cluster."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shlex
import subprocess
import traceback

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--existing-root', type=Path, required=True)
p.add_argument('--out-new', type=Path, required=True)
p.add_argument('--port', type=int, default=40881)
a = p.parse_args()
ROOT = Path(__file__).resolve().parent
out = a.out_new.resolve()
out.mkdir(parents=True, exist_ok=False)
os.umask(0o077)
os.nice(max(0, 10 - os.getpriority(os.PRIO_PROCESS, 0)))
prefix = a.existing_root / 'stage-v7assert' / str(a.existing_root / 'prefix').lstrip('/')
binpath = prefix / 'bin'
pins = json.loads((ROOT / 'SOURCE.json').read_text())
sha = lambda f: hashlib.sha256(Path(f).read_bytes()).hexdigest()
env = {k: v for k, v in os.environ.items() if not k.startswith('PG') and k not in ('LD_PRELOAD', 'LD_AUDIT', 'LD_LIBRARY_PATH')}
env.update(LD_LIBRARY_PATH=str(prefix / 'lib'), LC_ALL='C')
data = out / 'data'
commands = []
state = {'status': 'RUNNING', 'scope': 'untimed static helper oracle, not a candidate backend or SQL benchmark',
         'commands': commands, 'results': {}, 'modules': {}, 'port': a.port}
started = False
postmaster_pid = None

def run(args, log, timeout=180):
    q = subprocess.run(list(map(str, args)), capture_output=True, text=True, timeout=timeout, env=env)
    (out / log).write_text(q.stdout + q.stderr)
    commands.append({'args': list(map(str, args)), 'rc': q.returncode, 'log': log})
    if q.returncode:
        raise RuntimeError((log, q.returncode, q.stderr[-1500:]))
    return q.stdout

def sql(query, name):
    return run([binpath / 'psql', '-X', '-A', '-t', '-h', out, '-p', str(a.port),
                '-d', 'postgres', '-v', 'ON_ERROR_STOP=1', '-c', query], name).strip()

def inventory(root):
    return {str(f.relative_to(root)): {'bytes': f.stat().st_size, 'sha256': sha(f)}
            for f in sorted(root.rglob('*')) if f.is_file() and not f.is_symlink()}

try:
    before = inventory(prefix)
    expected = json.loads((a.existing_root / 'build-proof/v7assert/binding.json').read_text())['installed_files']
    assert before == expected
    assert sha(binpath / 'postgres') == '0440862d5ebc9353a770a6deca5cce61835881e983ef8b54b547d46594d1e4d0'
    inc = prefix / 'include/postgresql/server'
    internal = prefix / 'include/postgresql/internal'
    assert '#define USE_ASSERT_CHECKING 1' in (inc / 'pg_config.h').read_text()
    config = lambda name: subprocess.check_output([str(binpath / 'pg_config'), '--' + name], text=True).strip()
    flags = shlex.split(config('cflags')) + shlex.split(config('cppflags'))
    template = (ROOT / 'page-oracle.c.in').read_text()
    guard = (ROOT / 'source/V6/nbtsearch.c').read_text().split('int8search = ', 1)[1].split(';', 1)[0].replace('inskey.', 'key->')
    for role in ['V6', 'V8']:
        source = ROOT / 'source' / role / 'nbtsearch.c'
        assert sha(source) == pins['source_sha256'][role]
        name = 'firstattr_probe_' + role.lower()
        wrapper = out / (role + '-oracle.c')
        wrapper.write_text('#include "' + str(source) + '"\n' + template.replace('@NAME@', name).replace('@GUARD@', guard))
        obj = out / (role + '-oracle.o')
        module = out / (role + '-oracle.so')
        run(['gcc', *flags, '-fPIC', '-I' + str(inc), '-I' + str(internal), '-c', wrapper, '-o', obj], role + '-compile.log')
        run(['gcc', '-shared', '-o', module, obj], role + '-link.log')
        state['modules'][role] = {'path': str(module), 'sha256': sha(module), 'source_sha256': sha(source),
                                  'wrapper_sha256': sha(wrapper)}
    run([binpath / 'initdb', '-D', data, '--no-locale', '--encoding=UTF8'], 'initdb.log')
    run([binpath / 'pg_ctl', '-D', data, '-l', out / 'server.log', '-w', 'start', '-o',
         f'-p {a.port} -k {out} -c listen_addresses= -c shared_buffers=128MB -c autovacuum=off'], 'start.log')
    started = True
    postmaster_pid = int((data / 'postmaster.pid').read_text().splitlines()[0])
    assert sha(Path('/proc') / str(postmaster_pid) / 'exe') == sha(binpath / 'postgres')
    for role, module in state['modules'].items():
        name = 'firstattr_probe_' + role.lower()
        sql(f"CREATE FUNCTION {name}(regclass,bigint[]) RETURNS text AS '{module['path']}','{name}' LANGUAGE C STRICT;", role + '-create-function.out')
    setup = '''
    CREATE EXTENSION amcheck;
    CREATE EXTENSION pageinspect;
    CREATE TABLE payload(k bigint);
    INSERT INTO payload SELECT 2*g FROM generate_series(-25000,25000) g;
    INSERT INTO payload SELECT 3 FROM generate_series(1,50000);
    INSERT INTO payload VALUES ('-9223372036854775808'),('9223372036854775807'),(NULL),(NULL);
    CREATE INDEX payload_last ON payload(k);
    CREATE INDEX payload_first ON payload(k NULLS FIRST);
    CREATE TABLE distincts AS SELECT 2*g::bigint AS k FROM generate_series(-25000,25000) g;
    CREATE UNIQUE INDEX distincts_idx ON distincts(k);
    CREATE TABLE duplicates AS SELECT 3::bigint AS k FROM generate_series(1,5000);
    CREATE INDEX duplicates_idx ON duplicates(k);
    CREATE TABLE empty(k bigint);
    CREATE INDEX empty_idx ON empty(k);
    '''
    sql(setup, 'setup.out')
    sql('VACUUM ANALYZE;', 'vacuum.out')
    expected_rows = '100005|50001|5000'
    assert sql('SELECT (SELECT count(*) FROM payload),(SELECT count(*) FROM distincts),(SELECT count(*) FROM duplicates);', 'formula-counts.out') == expected_rows
    arguments = "ARRAY['-9223372036854775808',-50001,-50000,-49999,-1,0,1,2,3,4,5,49999,50000,50001,'9223372036854775807']::bigint[]"
    for index in ['payload_last', 'payload_first', 'distincts_idx', 'duplicates_idx', 'empty_idx']:
        answers = {role: sql(f"SELECT firstattr_probe_{role.lower()}('{index}',{arguments});", index + '-' + role + '.out') for role in state['modules']}
        assert len(set(answers.values())) == 1, (index, answers)
        numbers = list(map(int, answers['V8'].split(':')))
        assert len(numbers) == 4
        calls, leaves, internal_pages, checksum = numbers
        assert calls == (leaves + internal_pages) * 15 * 4
        if index in ['payload_last', 'payload_first', 'distincts_idx']:
            assert leaves > 0 and internal_pages > 0
        state['results'][index] = {'answers': answers, 'calls_each_role': calls, 'leaf_pages': leaves,
                                    'internal_pages': internal_pages, 'checksum': checksum}
        sql(f"SELECT bt_index_parent_check('{index}',true,true);", index + '-amcheck.out')
    state['pivot_shapes'] = sql("SELECT p.type,count(*) FILTER(WHERE i.nulls),count(*) FILTER(WHERE i.htid IS NOT NULL),count(*) FILTER(WHERE i.htid IS NULL AND i.data<>'') FROM generate_series(1,pg_relation_size('payload_last')/8192-1)b CROSS JOIN LATERAL bt_page_stats('payload_last',b)p CROSS JOIN LATERAL bt_page_items('payload_last',b)i WHERE p.type IN('i','r') GROUP BY p.type ORDER BY p.type;", 'pivot-shapes.out')
    state['installed_files_before_after_equal'] = inventory(prefix) == before
    assert state['installed_files_before_after_equal']
    state['status'] = 'PASS_ASSERT_LOCKED_LEAF_INTERNAL_LINEAR_ORACLE'
except BaseException as e:
    state.update(status='FAIL', error=repr(e), traceback=traceback.format_exc())
    raise
finally:
    if started or (data / 'postmaster.pid').exists():
        run([binpath / 'pg_ctl', '-D', data, '-m', 'fast', '-w', 'stop'], 'stop.log', timeout=90)
    q = subprocess.run([str(binpath / 'pg_ctl'), '-D', str(data), 'status'], capture_output=True, text=True, env=env)
    state['cleanup'] = {'pg_ctl_status_rc': q.returncode, 'postmaster_pidfile_absent': not (data / 'postmaster.pid').exists(),
                        'postmaster_pid': postmaster_pid, 'pid_absent': postmaster_pid is None or not (Path('/proc') / str(postmaster_pid)).exists(),
                        'socket_absent': not (out / ('.s.PGSQL.' + str(a.port))).exists()}
    (out / 'receipt.json').write_text(json.dumps(state, indent=2) + '\n')
    assert q.returncode == 3 and state['cleanup']['postmaster_pidfile_absent'] and state['cleanup']['pid_absent'] and state['cleanup']['socket_absent']
print(state['status'])
