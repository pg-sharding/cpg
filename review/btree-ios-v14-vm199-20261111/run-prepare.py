#!/usr/bin/env python3
"""Queue immutable IOS build and finite checks; stop for actual smoke review."""
from pathlib import Path
import fcntl
import importlib.util
import json
import os
import socket
import subprocess
import sys
import time
import traceback

ROOT = Path(__file__).resolve().parent
INPUTS = ROOT / 'inputs-r1'
GIN = ROOT.parent / 'c9-199-1111'
assert str(ROOT) == '/home/reshke/wpgpg/ios14-199-1111'
loader = importlib.util.spec_from_file_location('ios_common', INPUTS / 'build-harness/common.py')
bc = importlib.util.module_from_spec(loader)
loader.loader.exec_module(bc)
state = dict(status='RUNNING', phase='wait-gin', pid=os.getpid(), started_ns=time.time_ns(),
             host='51.250.5.199', timing_samples=0)

def save():
    bc.save(ROOT / 'PREPARE-r1.json', state)

def run(name, args):
    state['phase'] = name
    save()
    return bc.run(args, ROOT / (name + '.log'), cwd=ROOT, timeout=14400)

def seed(receipt):
    prefix = Path(receipt['variants']['B']['prefix'])
    data, sock = ROOT / 'correctness-seed', ROOT / 'seed-socket'
    sock.mkdir(mode=0o700)
    assert len(os.fsencode(sock / '.s.PGSQL.40648')) < 104
    bc.run([prefix / 'bin/initdb', '-D', data, '--no-locale', '-E', 'UTF8', '-A', 'trust'],
           ROOT / 'seed-initdb.log', prefix=prefix)
    sql = ROOT / 'create-correctness-seed.sql'
    sql.write_text('''CREATE EXTENSION amcheck;
CREATE TABLE wide AS
SELECT g, repeat((g%10000)::text,8) COLLATE "C" AS i,
       repeat((g%10000)::text,9) COLLATE "C" AS j
FROM generate_series(1,200000) g;
CREATE INDEX wide_idx ON wide(i,j);
VACUUM (FREEZE,ANALYZE) wide;
CHECKPOINT;
SELECT count(*),sum(length(i)) FROM wide;
''')
    proof = dict(recipe='Previously documented replacement seed, executed anew on baseline only',
                 sql_sha256=bc.sha(sql), started_ns=time.time_ns(), timing_samples=0)
    try:
        bc.run([prefix / 'bin/pg_ctl', '-D', data, '-l', ROOT / 'seed-postmaster.log',
                '-o', f'-k {sock} -p 40648 -c listen_addresses= -c autovacuum=off', '-w', 'start'],
               ROOT / 'seed-start.log', prefix=prefix)
        pid = int((data / 'postmaster.pid').read_text().splitlines()[0])
        assert bc.sha(Path('/proc', str(pid), 'exe')) == receipt['variants']['B']['postgres_sha256']
        proof['pid'] = pid
        bc.run([prefix / 'bin/psql', '-X', '-h', sock, '-p', '40648', '-d', 'postgres',
                '-v', 'ON_ERROR_STOP=1', '-f', sql], ROOT / 'seed-setup.log', prefix=prefix)
    finally:
        if (data / 'postmaster.pid').exists():
            bc.run([prefix / 'bin/pg_ctl', '-D', data, '-m', 'fast', '-w', 'stop'],
                   ROOT / 'seed-stop.log', prefix=prefix)
        proof['stop'] = bc.stopped(prefix, data)
        assert not (sock / '.s.PGSQL.40648').exists()
        proof['finished_ns'] = time.time_ns()
        bc.save(ROOT / 'CORRECTNESS-SEED-r1.json', proof)

def main():
    save()
    lock = None
    try:
        deadline = time.monotonic() + 21600
        while True:
            p = GIN / 'CAMPAIGNS-r1.json'
            d = json.loads(p.read_text()) if p.exists() else {}
            if str(d.get('status', '')).startswith('FAILED'):
                raise RuntimeError(('GIN predecessor failed; inspect before continuing', d.get('error')))
            if d.get('status') == 'PASS':
                break
            assert time.monotonic() < deadline, 'predecessor deadline'
            time.sleep(10)
        lock = (ROOT.parent / 'vm199-benchmark.lock').open('a')
        fcntl.flock(lock, fcntl.LOCK_EX)
        bc.nice10()
        assert {4, 6} <= os.sched_getaffinity(0)
        topo = subprocess.check_output(['lscpu', '-p=CPU,CORE,SOCKET'], text=True)
        core = {int(s[0]): s[1:] for l in topo.splitlines() if not l.startswith('#') for s in [l.split(',')]}
        assert core[4] != core[6]
        ports = list(range(40640, 40644)) + [40648, 40649] + list(range(40750, 40754)) + list(range(40759, 40764))
        for port in ports:
            with socket.socket() as sock:
                sock.bind(('127.0.0.1', port))
        bc.save(ROOT / 'HOST-r1.json', dict(utc_ns=time.time_ns(), uname=list(os.uname()),
                  topology=topo, cpu=json.loads(subprocess.check_output(['lscpu', '-J'], text=True)),
                  load=list(os.getloadavg()), mem=Path('/proc/meminfo').read_text(),
                  versions=subprocess.check_output(['dpkg-query', '-W', 'gcc-13', 'gdb', 'make', 'bison', 'flex', 'libssl-dev', 'zlib1g-dev'], text=True),
                  ports_unused=ports, predecessor_sha256=bc.sha(GIN / 'CAMPAIGNS-r1.json')))
        run('build', [sys.executable, '-B', INPUTS / 'build-harness/build.py',
                     '--source-archive', GIN / 'baseline-B72.tar.gz',
                     '--source-plan', INPUTS / 'source/SOURCE.json', '--output', ROOT / 'build',
                     '--core-port', '40640'])
        receipt = bc.checked_build(ROOT / 'build')
        state['phase'] = 'correctness-seed'
        save()
        seed(receipt)
        run('qualification', [sys.executable, '-B', INPUTS / 'qualification/gate.py',
                              '--build', ROOT / 'build', '--correctness-seed', ROOT / 'correctness-seed',
                              '--output', ROOT / 'qualification', '--port', '40649'])
        run('materialize-sql', [sys.executable, '-B', INPUTS / 'prepare-sql.py',
                               '--build', ROOT / 'build', '--qualification', ROOT / 'qualification',
                               '--output', ROOT / 'sql'])
        run('prepare-sql', [sys.executable, '-B', ROOT / 'sql/sql-controller.py', 'prepare'])
        run('smoke-sql', [sys.executable, '-B', ROOT / 'sql/sql-controller.py', 'smoke'])
        run('review-smoke', [sys.executable, '-B', INPUTS / 'review-smoke.py',
                            '--collection', ROOT, '--inputs', INPUTS, '--output', ROOT / 'SMOKE-REVIEW-r1.json'])
        bc.checked_build(ROOT / 'build')
        state.update(status='READY_FOR_ROOT_SMOKE_REVIEW', phase='complete', timing_samples=0)
    except BaseException as exc:
        state.update(status='FAILED_PRESERVED', error=repr(exc), traceback=traceback.format_exc())
        raise
    finally:
        state['finished_ns'] = time.time_ns()
        save()
        if lock:
            fcntl.flock(lock, fcntl.LOCK_UN)

if __name__ == '__main__':
    main()
