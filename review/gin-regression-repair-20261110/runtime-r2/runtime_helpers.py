"""Actual-AM module qualification and separate owned-backend software profiles."""
import gzip
import hashlib
import json
import pathlib
import shlex
import shutil
import subprocess
import time


def compile_micro(root, out, prefix, bc):
    source = root / 'gin-am-micro.c'
    pg = prefix / 'bin/pg_config'
    flags = shlex.split(bc.capture([pg, '--cflags'], prefix)) + shlex.split(bc.capture([pg, '--cppflags'], prefix))
    headers = pathlib.Path(bc.capture([pg, '--includedir-server'], prefix).strip())
    obj, module = out / 'gin-am-micro.o', out / 'gin-am-micro.so'
    bc.run(['gcc', *flags, '-Werror', '-fPIC', '-I' + str(headers),
            '-I' + str(prefix / 'include'), '-c', source, '-o', obj], out / 'micro-compile.log', prefix=prefix)
    bc.run(['gcc', '-shared', '-fno-lto', obj, '-o', module], out / 'micro-link.log', prefix=prefix)
    bc.save(out / 'module.json', dict(status='PASS_COMPILE', source_sha256=bc.sha(source),
            module_sha256=bc.sha(module), prefix=str(prefix),
            headers_sha256=hashlib.sha256(json.dumps(bc.inventory(headers), sort_keys=True).encode()).hexdigest(),
            scope='Real index_rescan/index_getbitmap/tbm_free loop; no modeled loader, private GIN structure or extracted scan body.'))
    return module


def qualify_micro(session, cases):
    result = {}
    for c in cases:
        query = c['sql'].rsplit(', ', 1)[0] + ', 2)'
        value = session.json(query)
        assert value['loops'] == 2 and value['total_tids'] == c['tids_per_scan'] * 2
        assert value['cpu_ns'] > 0 and value['wall_ns'] > 0
        result[c['name']] = value
    return result


def profile(session, case, out, bc):
    out.mkdir()
    perf = shutil.which('perf')
    result = dict(status='RUNNING', backend_pid=session.pid, case=case['name'], calls=0,
                  scope='Separate diagnostic original-query loop, not an accepted latency benchmark or PMU attribution.')
    if not perf:
        result.update(status='UNAVAILABLE', error='perf executable missing')
        bc.save(out / 'status.json', result)
        return result
    data = out / 'perf.data'
    stderr = out / 'record-stderr.txt'
    command = [perf, 'record', '-e', 'cpu-clock:u', '-F', '199', '-p', str(session.pid),
               '--call-graph', 'dwarf,8192', '-o', str(data), '--', 'sleep', '3']
    result.update(command=command, started_ns=time.time_ns())
    session.sql("RESET enable_seqscan;RESET enable_bitmapscan;RESET enable_indexscan;RESET enable_indexonlyscan;SET work_mem='64MB';" + case['settings'])
    before = session.snapshot()
    start = time.monotonic_ns()
    with stderr.open('xb') as err:
        proc = subprocess.Popen(command, stdout=subprocess.DEVNULL, stderr=err,
                                stdin=subprocess.DEVNULL, start_new_session=True)
        try:
            while proc.poll() is None:
                assert session.sql(case['sql']) == case['answer']
                result['calls'] += 1
        finally:
            try:
                proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                proc.terminate()
                proc.wait(timeout=10)
    result.update(returncode=proc.returncode, client_wall_ns=time.monotonic_ns() - start,
                  command_delta={k: v - before[k] for k, v in session.snapshot().items()},
                  finished_ns=time.time_ns(), record_diagnostic=stderr.read_text()[-2000:])
    if proc.returncode:
        result['status'] = 'UNAVAILABLE'
    else:
        script = subprocess.run([perf, 'script', '-i', str(data)], stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE, timeout=90)
        result['script_returncode'] = script.returncode
        if script.returncode:
            result.update(status='UNAVAILABLE', script_diagnostic=script.stderr.decode(errors='replace')[-1000:])
        else:
            payload = gzip.compress(script.stdout, mtime=0)
            (out / 'stacks.txt.gz').write_bytes(payload)
            result.update(status='PASS', stack_text_sha256=hashlib.sha256(script.stdout).hexdigest(),
                          stack_text_bytes=len(script.stdout),
                          sample_blocks=sum(bool(x.strip()) for x in script.stdout.split(b'\n\n')))
            summary = subprocess.run([perf, 'report', '-i', str(data), '--stdio', '--no-children',
                                      '--sort=symbol', '--percent-limit', '0.5'],
                                     stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=90)
            (out / 'symbols.txt').write_bytes(summary.stdout)
            result['report_returncode'] = summary.returncode
    bc.save(out / 'status.json', result)
    return result
