"""Bounded local helpers for fresh B/N/H/C hash builds and synthetic seed."""
import hashlib
import json
import os
import pathlib
import signal
import subprocess
import time

HERE = pathlib.Path(__file__).resolve().parent
BASE = '72b9498df9a369e747f8d96efb5a6cd33c2451e2'
ROLES = ('B', 'N', 'H', 'C')


def sha(path):
    return hashlib.sha256(pathlib.Path(path).read_bytes()).hexdigest()


def save(path, value):
    path = pathlib.Path(path)
    temporary = path.with_name(path.name + '.tmp')
    temporary.write_text(json.dumps(value, indent=2) + '\n')
    with temporary.open('rb') as stream:
        os.fsync(stream.fileno())
    temporary.replace(path)


def nice10():
    def terminate(signum, frame):
        raise KeyboardInterrupt('termination requested')
    signal.signal(signal.SIGTERM, terminate)
    current = os.getpriority(os.PRIO_PROCESS, 0)
    if current < 10:
        os.nice(10 - current)
    assert os.getpriority(os.PRIO_PROCESS, 0) == 10


def env(prefix=None):
    result = {k: v for k, v in os.environ.items()
              if not k.startswith('PG') and k not in {
                  'MAKEFLAGS', 'MFLAGS', 'CFLAGS', 'CPPFLAGS', 'LDFLAGS',
                  'CC', 'CXX', 'LD_PRELOAD', 'LD_LIBRARY_PATH'}}
    result.update(LC_ALL='C', GIT_OPTIONAL_LOCKS='0', GIT_NO_LAZY_FETCH='1',
                  GIT_ALLOW_PROTOCOL='', GIT_CONFIG_NOSYSTEM='1',
                  GIT_CONFIG_GLOBAL='/dev/null')
    if prefix:
        result['LD_LIBRARY_PATH'] = str(pathlib.Path(prefix) / 'lib')
    return result


def run(args, log, *, cwd=None, prefix=None, timeout=3600, environment=None):
    """Record even failed commands; terminate only our own new process group."""
    args = list(map(str, args))
    log = pathlib.Path(log)
    record = dict(args=args, cwd=str(cwd) if cwd else None,
                  started_ns=time.time_ns(), log=str(log))
    proc = None
    try:
        with log.open('xb') as stream:
            proc = subprocess.Popen(args, cwd=cwd, env=environment or env(prefix),
                                    stdout=stream, stderr=subprocess.STDOUT,
                                    start_new_session=True)
            record['pid'] = proc.pid
            record['returncode'] = proc.wait(timeout=timeout)
    except BaseException as exc:
        record['exception'] = repr(exc)
        if proc and proc.poll() is None:
            try:
                os.killpg(proc.pid, signal.SIGTERM)
            except ProcessLookupError:
                pass
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                try:
                    os.killpg(proc.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                proc.wait(timeout=5)
        raise
    finally:
        if proc:
            record['returncode'] = proc.poll()
        record['finished_ns'] = time.time_ns()
        if log.exists():
            record['log_sha256'] = sha(log)
        save(log.with_suffix(log.suffix + '.command.json'), record)
    assert record['returncode'] == 0, (args[0], record['returncode'], str(log))
    return record


def capture(args, prefix=None):
    return subprocess.check_output(list(map(str, args)), env=env(prefix), text=True)


def inventory(root, allow_symlinks=False):
    root = pathlib.Path(root)
    result = {}
    for path in sorted(root.rglob('*')):
        name = path.relative_to(root).as_posix()
        if path.is_symlink():
            assert allow_symlinks, (path, 'unexpected source/PGDATA symlink')
            result[name] = dict(symlink=os.readlink(path))
        elif path.is_file():
            result[name] = dict(bytes=path.stat().st_size, sha256=sha(path))
    return result


def sync(root):
    root = pathlib.Path(root)
    for path in root.rglob('*'):
        assert not path.is_symlink()
        if path.is_file():
            with path.open('rb') as stream:
                os.fsync(stream.fileno())
    directories = [root] + [p for p in root.rglob('*') if p.is_dir()]
    for path in sorted(directories, key=lambda p: len(p.parts), reverse=True):
        descriptor = os.open(path, os.O_RDONLY)
        try:
            os.fsync(descriptor)
        finally:
            os.close(descriptor)


def stopped(prefix, data):
    prefix, data = pathlib.Path(prefix), pathlib.Path(data)
    result = subprocess.run([str(prefix / 'bin/pg_ctl'), '-D', str(data), 'status'],
                            env=env(prefix), capture_output=True, timeout=30)
    control = capture([prefix / 'bin/pg_controldata', data], prefix)
    state = next(line.split(':', 1)[1].strip() for line in control.splitlines()
                 if line.startswith('Database cluster state:'))
    assert result.returncode == 3 and state == 'shut down'
    assert not (data / 'postmaster.pid').exists()
    return dict(pg_ctl_status_rc=3, cluster_state=state, pidfile_absent=True)


def source_plan(path):
    path = pathlib.Path(path).resolve()
    spec = json.loads(path.read_text())
    assert spec['base'] == BASE and spec['files'] == 7726
    assert set(spec['variants']) == set(ROLES)
    assert spec['variants']['B']['commit'] == BASE
    assert spec['variants']['B']['source_files'] == {}
    manifest_path = path.parent / 'base-source-files.json'
    manifest = json.loads(manifest_path.read_text())
    expected = {name: {k: value[k] for k in ('bytes', 'sha256')}
                for name, value in manifest.items()}
    assert len(expected) == 7726
    for role in ROLES:
        variant = spec['variants'][role]
        assert len(variant['commit']) == 40
        patch = path.parent / variant['patch']['path']
        assert sha(patch) == variant['patch']['sha256']
        for name, value in variant['source_files'].items():
            assert name in expected and not pathlib.PurePosixPath(name).is_absolute()
            assert '..' not in pathlib.PurePosixPath(name).parts
            snapshot = path.parent / role / name
            assert snapshot.stat().st_size == value['bytes']
            assert sha(snapshot) == value['sha256']
    assert set(spec['variants']['N']['source_files']) == {
        'src/backend/access/hash/hashsearch.c'}
    assert set(spec['variants']['H']['source_files']) == set(
        spec['variants']['C']['source_files'])
    return spec, expected


def checked_build(path):
    path = pathlib.Path(path).resolve()
    receipt = json.loads((path / 'build-receipt.json').read_text())
    assert receipt['status'] == 'PASS_NEW_MATCHED_HASH_BUILDS'
    assert json.loads((path / 'status.json').read_text())['status'] == receipt['status']
    assert receipt['base'] == BASE and receipt['core239_each'] is True
    assert set(receipt['variants']) == {'B', 'N', 'H', 'C', 'C_assert'}
    assert receipt['role_to_variant'] == {'B': 'B', 'T': 'B', 'N': 'N', 'H': 'H', 'C': 'C'}
    assert sha(receipt['support']) == receipt['support_sha256']
    for variant in receipt['variants'].values():
        prefix = pathlib.Path(variant['prefix'])
        assert sha(prefix / 'bin/postgres') == variant['postgres_sha256']
        assert inventory(prefix, allow_symlinks=True) == variant['installed_files']
    return receipt


def socket_directory(path, port):
    path = pathlib.Path(path)
    assert len(os.fsencode(path / ('.s.PGSQL.' + str(port)))) < 104
    path.mkdir(mode=0o700)
    return path


def local_dsn(socket, port):
    value = str(socket).replace('\\', '\\\\').replace("'", "\\'")
    return "host='" + value + "' port=" + str(port) + ' dbname=postgres'
