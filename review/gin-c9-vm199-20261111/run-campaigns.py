#!/usr/bin/env python3
"""Run the two predeclared campaigns after the relocated build; sample host load."""
from pathlib import Path
import argparse
import fcntl
import hashlib
import json
import os
import subprocess
import sys
import threading
import time
import traceback

ROOT = Path(__file__).resolve().parent
assert str(ROOT) == '/home/reshke/wpgpg/c9-199-1111'
STATE = ROOT / 'CAMPAIGNS-r1.json'

def save(value):
    p = STATE.with_suffix('.tmp')
    p.write_text(json.dumps(value, indent=2) + '\n')
    p.replace(STATE)

def sample():
    cpus = {s[0]: list(map(int, s[1:])) for l in Path('/proc/stat').read_text().splitlines()
            for s in [l.split()] if s and s[0].startswith('cpu')}
    mem = {k: v.strip() for l in Path('/proc/meminfo').read_text().splitlines()
           for k, v in [l.split(':', 1)] if k in ('MemTotal', 'MemAvailable', 'SwapFree')}
    processes = []
    for p in Path('/proc').iterdir():
        if not p.name.isdigit():
            continue
        try:
            text = (p / 'stat').read_text()
            comm = text[text.index('(') + 1:text.rindex(')')]
            fields = text[text.rindex(')') + 2:].split()
            processes.append(dict(pid=int(p.name), comm=comm,
                                  ticks=int(fields[11]) + int(fields[12]),
                                  start_ticks=int(fields[19])))
        except (FileNotFoundError, PermissionError, ProcessLookupError):
            pass
    return dict(utc_ns=time.time_ns(), monotonic_ns=time.monotonic_ns(), cpus=cpus,
                memory=mem, load=list(os.getloadavg()), processes=processes)

def main():
    p = argparse.ArgumentParser()
    p.add_argument('--launch', action='store_true')
    args = p.parse_args()
    if args.launch:
        assert not STATE.exists()
        with (ROOT / 'campaign-controller-r1.log').open('xb') as log:
            proc = subprocess.Popen([sys.executable, '-B', __file__], cwd=ROOT,
                                    stdin=subprocess.DEVNULL, stdout=log,
                                    stderr=subprocess.STDOUT, start_new_session=True)
        print(json.dumps(dict(status='LAUNCHED', pid=proc.pid)))
        return
    state = dict(status='RUNNING', phase='wait-build', pid=os.getpid(),
                 started_ns=time.time_ns(), phases={}, host='51.250.5.199')
    save(state)
    lock = (ROOT.parent / 'vm199-benchmark.lock').open('a')
    fcntl.flock(lock, fcntl.LOCK_EX)
    stop = threading.Event()
    def monitor():
        with (ROOT / 'HOST-SAMPLES-r1.jsonl').open('x') as stream:
            while True:
                stream.write(json.dumps(sample(), separators=(',', ':')) + '\n')
                stream.flush()
                if stop.wait(5):
                    break
    watcher = None
    try:
        deadline = time.monotonic() + 10800
        while True:
            path = ROOT / 'build-r2/status.json'
            b = json.loads(path.read_text()) if path.exists() else {}
            if str(b.get('status', '')).startswith('FAILED'):
                raise RuntimeError(('build failed', b.get('error')))
            if b.get('status') == 'PASS_GIN_REPAIR_R3_BUILDS':
                assert not b.get('core_cleanup_errors')
                break
            assert time.monotonic() < deadline, 'build deadline'
            time.sleep(10)
        watcher = threading.Thread(target=monitor, daemon=True)
        watcher.start()
        for mode, port, raw, retained, clusters in [('screen', 44800, 2688, 2304, 19),
                                                    ('full', 44900, 2800, 2400, 15)]:
            state['phase'] = mode
            save(state)
            out = ROOT / (mode + '-r1')
            cmd = [sys.executable, '-B', str(ROOT / 'inputs-r1/followup-r3/campaign.py'),
                   '--build', str(ROOT / 'build-r2'), '--output', str(out),
                   '--mode', mode, '--first-port', str(port)]
            phase = dict(argv=cmd, started_ns=time.time_ns())
            state['phases'][mode] = phase
            save(state)
            with (ROOT / (mode + '-controller-r1.log')).open('xb') as log:
                result = subprocess.run(cmd, cwd=ROOT, stdin=subprocess.DEVNULL,
                                        stdout=log, stderr=subprocess.STDOUT)
            phase.update(finished_ns=time.time_ns(), returncode=result.returncode)
            save(state)
            assert result.returncode == 0, mode
            s = json.loads((out / 'status.json').read_text())
            assert s['status'] == 'PASS' and not s['cleanup_errors']
            assert s['raw'] == raw and s['retained'] == retained
            assert len(s['clusters']) == clusters and all(x['stopped'] for x in s['clusters'])
            for c in (0, 1):
                a = json.loads((out / ('analysis' + str(c)) / 'status.json').read_text())
                assert str(a['status']).startswith('PASS'), a
            phase['checked_status_sha256'] = hashlib.sha256((out / 'status.json').read_bytes()).hexdigest()
            save(state)
        state.update(status='PASS', phase='complete', raw=5488, retained=4704, warm=784)
    except BaseException as exc:
        state.update(status='FAILED_PRESERVED', error=repr(exc), traceback=traceback.format_exc())
        raise
    finally:
        stop.set()
        if watcher:
            watcher.join(10)
        state['finished_ns'] = time.time_ns()
        save(state)
        fcntl.flock(lock, fcntl.LOCK_UN)

if __name__ == '__main__':
    main()
