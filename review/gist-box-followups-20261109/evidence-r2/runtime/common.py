"""Local runtime helpers for the fresh complete BOX backends."""
import hashlib
import json
import os
from pathlib import Path
import select
import signal
import subprocess
import time

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
BUILD = ROOT / 'builds'
ROLES = ('B', 'T', 'R', 'C', 'D')

def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def save(p, value):
    p = Path(p)
    temporary = p.with_name(p.name + '.tmp')
    with temporary.open('w') as f:
        json.dump(value, f, indent=2)
        f.write('\n')
        f.flush()
        os.fsync(f.fileno())
    temporary.replace(p)

def append(p, value):
    with Path(p).open('a') as f:
        f.write(json.dumps(value) + '\n')
        f.flush()
        os.fsync(f.fileno())

def env(prefix):
    e = {k:v for k,v in os.environ.items() if not k.startswith('PG') and k not in ('LD_PRELOAD', 'LD_AUDIT', 'LD_LIBRARY_PATH')}
    e.update(LD_LIBRARY_PATH=str(prefix / 'lib'), LC_ALL='C')
    return e

def inventory(root):
    result = {}
    for p in sorted(Path(root).rglob('*')):
        if p.is_symlink():
            result[str(p.relative_to(root))] = {'symlink': os.readlink(p)}
        elif p.is_file():
            result[str(p.relative_to(root))] = {'bytes': p.stat().st_size, 'sha256': sha(p)}
    return result

def fsync_tree(root):
    root = Path(root)
    for p in root.rglob('*'):
        if p.is_file() and not p.is_symlink():
            with p.open('rb') as f:
                os.fsync(f.fileno())
    for p in sorted([root] + [p for p in root.rglob('*') if p.is_dir()], key=lambda p: len(p.parts), reverse=True):
        fd = os.open(p, os.O_RDONLY)
        try: os.fsync(fd)
        finally: os.close(fd)

def builds():
    r = json.loads((BUILD / 'build-receipt.json').read_text())
    assert r['status'] == 'PASS_NEW_MATCHED_BOX_BUILDS' and r['core239_each']
    state = json.loads((BUILD / 'status.json').read_text())
    assert state['status'] == r['status'] and not state['core_cleanup_errors']
    assert sha(ROOT / 'source/SOURCE.json') == r['source_plan_sha256']
    assert set(r['variants']) == {'B','R','C','D','C_assert','D_assert'}
    for name, v in r['variants'].items():
        p = Path(v['prefix'])
        assert sha(p / 'bin/postgres') == v['postgres_sha256']
        assert inventory(p) == v['installed_files']
    return r

class Runtime:
    def __init__(self, out):
        def terminate(signum, frame):
            raise KeyboardInterrupt('termination requested')
        signal.signal(signal.SIGTERM, terminate)
        self.out = Path(out)
        self.receipt = builds()
        self.owned = []
        self.pids = set()
        self.backends = set()
        self.sessions = []

    def variant(self, role): return 'B' if role == 'T' else role
    def prefix(self, role): return Path(self.receipt['variants'][self.variant(role)]['prefix'])

    def run(self, role, args, name, timeout=300):
        with (self.out / name).open('xb') as f:
            q = subprocess.run(list(map(str,args)), stdout=f, stderr=subprocess.STDOUT, timeout=timeout, env=env(self.prefix(role)))
        assert q.returncode == 0, (name, q.returncode)

    def start(self, role, data, tag, cpu=None):
        data = Path(data)
        socket = ROOT / ('s-' + tag)
        socket.mkdir(mode=0o700)
        port = 40920
        assert len(os.fsencode(socket / ('.s.PGSQL.' + str(port)))) < 104
        rec = {'role': role, 'data': str(data), 'socket': str(socket), 'port': port, 'started_ns': time.time_ns()}
        self.owned.append(rec)
        command = [self.prefix(role)/'bin/pg_ctl','-D',data,'-l',self.out/(tag+'-server.log'),'-o',
                   f'-p{port} -k{socket} -c listen_addresses= -c shared_buffers=256MB -c work_mem=64MB -c jit=off -c autovacuum=off -c max_parallel_workers_per_gather=0 -c checkpoint_timeout=1h -c log_checkpoints=off', '-w','start']
        if cpu is not None: command = ['taskset','-c',str(cpu)] + command
        self.run(role, command, tag+'-start.log')
        pid = int((data/'postmaster.pid').read_text().splitlines()[0])
        rec.update(pid=pid, ready_ns=time.time_ns(), postgres_sha256=sha(Path('/proc')/str(pid)/'exe'))
        self.pids.add(pid)
        assert rec['postgres_sha256'] == self.receipt['variants'][self.variant(role)]['postgres_sha256']
        return rec

    def open(self, rec):
        session = Session(self, rec)
        self.sessions.append(session)
        self.backends.add(session.pid)
        return session

    def stop(self, rec):
        p = self.prefix(rec['role'])
        data = Path(rec['data'])
        if (data/'postmaster.pid').exists():
            pid = int((data/'postmaster.pid').read_text().splitlines()[0])
            self.pids.add(pid)
            assert sha(Path('/proc')/str(pid)/'exe') == self.receipt['variants'][self.variant(rec['role'])]['postgres_sha256']
            self.run(rec['role'], [p/'bin/pg_ctl','-D',data,'-m','fast','-w','stop'], Path(rec['socket']).name+'-stop.log',90)
        q = subprocess.run([str(p/'bin/pg_ctl'),'-D',str(data),'status'], env=env(p),capture_output=True,timeout=20)
        assert q.returncode==3 and not (data/'postmaster.pid').exists()
        assert not (Path(rec['socket'])/('.s.PGSQL.'+str(rec['port']))).exists()
        assert 'pid' not in rec or not (Path('/proc')/str(rec['pid'])).exists()
        self.owned.remove(rec)
        return dict(rec, stopped=True)

    def cleanup(self):
        errors=[]
        for s in self.sessions:
            try: s.close()
            except BaseException as e: errors.append(repr(e))
        stopped=[]
        for r in list(reversed(self.owned)):
            try: stopped.append(self.stop(r))
            except BaseException as e: errors.append(repr(e))
        proof={'errors':errors,'stopped':stopped,'remaining_owned':len(self.owned),
               'postmaster_pids':sorted(self.pids),'backend_pids':sorted(self.backends),
               'pids_absent':all(not (Path('/proc')/str(p)).exists() for p in self.pids|self.backends)}
        return proof

class Session:
    def __init__(self, runtime, rec):
        self.runtime=runtime
        self.rec=rec
        self.buffer=b''
        self.closed=False
        self.err=(runtime.out/('psql-'+rec['role']+'-'+str(time.time_ns())+'.stderr')).open('xb')
        self.p=subprocess.Popen([str(runtime.prefix('B')/'bin/psql'),'-XAtq','-h',rec['socket'],'-p',str(rec['port']),'-d','postgres','-v','ON_ERROR_STOP=1'],
                                stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=self.err,bufsize=0,env=env(runtime.prefix('B')),start_new_session=True)
        try:
            self.command("SET statement_timeout='90s';SET jit=off;SET max_parallel_workers_per_gather=0;SET enable_memoize=off;SET timing_clock_source=system;SET work_mem='64MB';")
            self.pid=int(self.command('SELECT pg_backend_pid();'))
            assert sha(Path('/proc')/str(self.pid)/'exe')==rec['postgres_sha256']
            self.metadata={'pid':self.pid,'client_pid':self.p.pid,'affinity':sorted(os.sched_getaffinity(self.pid)),
                           'postgres_sha256':rec['postgres_sha256'],'maps':(Path('/proc')/str(self.pid)/'maps').read_text(),
                           'settings':json.loads(self.command("SELECT json_object_agg(name,setting) FROM pg_settings WHERE source<>'default';"))}
        except BaseException:
            self.close()
            raise

    def command(self, sql, timeout=100):
        self.p.stdin.write((sql+'\n\\echo __BOX_COMPLETE__\n').encode())
        self.p.stdin.flush()
        lines=[]
        deadline=time.monotonic()+timeout
        while True:
            if b'\n' in self.buffer:
                line,self.buffer=self.buffer.split(b'\n',1)
                if line.strip()==b'__BOX_COMPLETE__':return b'\n'.join(lines).decode().strip()
                lines.append(line)
                continue
            remaining=deadline-time.monotonic()
            if remaining<=0:raise TimeoutError('psql response timeout')
            ready,_,_=select.select([self.p.stdout],[],[],remaining)
            if not ready:raise TimeoutError('psql response timeout')
            chunk=os.read(self.p.stdout.fileno(),65536)
            if not chunk:raise RuntimeError('psql exited '+str(self.p.poll()))
            self.buffer+=chunk

    def snapshot(self):
        p=Path('/proc')/str(self.pid)
        cpu,queue,slices=map(int,(p/'schedstat').read_text().split())
        io={a.strip():int(b) for a,b in (line.split(':',1) for line in (p/'io').read_text().splitlines())}
        return {'cpu_ns':cpu,'runqueue_ns':queue,'slices':slices,'read_bytes':io['read_bytes'],'write_bytes':io['write_bytes']}

    def measure(self, sql, native=False):
        before=self.snapshot()
        start=time.monotonic_ns()
        raw=self.command(sql+';' if native else 'EXPLAIN(ANALYZE,BUFFERS,WAL,TIMING OFF,FORMAT JSON) '+sql+';')
        wall=time.monotonic_ns()-start
        after=self.snapshot()
        result={'raw':raw,'command_start_ns':start,'client_wall_ms':wall/1e6,
                'before':before,'after':after,'delta':{k:after[k]-before[k] for k in before}}
        result['command_cpu_ms']=result['delta']['cpu_ns']/1e6
        if native:
            result['native']=json.loads(raw)
            result['primary_ms']=result['native']['cpu_ns']/1e6
        else:
            result['plan']=json.loads(raw)[0]
            result['primary_ms']=result['plan']['Execution Time']
        return result

    def close(self):
        if self.closed:return
        if self.p.poll() is None:
            try:self.p.stdin.close();self.p.wait(timeout=10)
            except (BrokenPipeError,subprocess.TimeoutExpired):
                try:os.killpg(self.p.pid,signal.SIGTERM)
                except ProcessLookupError:pass
                self.p.wait(timeout=10)
        self.p.stdout.close()
        self.err.close()
        self.closed=True
