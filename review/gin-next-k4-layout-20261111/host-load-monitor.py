#!/usr/bin/env python3
"""Bounded Linux CPU observation on a spare core; no process commands or signals."""
import argparse
import json
import os
import pathlib
import time


def snapshot():
    processes = {}
    for path in pathlib.Path('/proc').glob('[0-9]*/stat'):
        try:
            data = path.read_text()
            end = data.rindex(')')
            fields = data[end + 2:].split()
            # Field 22 (starttime) distinguishes PID reuse. Fields 14/15 are CPU.
            key = (int(path.parent.name), int(fields[19]))
            processes[key] = (data[data.index('(') + 1:end], int(fields[11]) + int(fields[12]))
        except (FileNotFoundError, ProcessLookupError, PermissionError):
            continue
    return processes


def save(path, value):
    temporary = path.with_suffix('.tmp')
    temporary.write_text(json.dumps(value, indent=2) + '\n')
    temporary.replace(path)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=pathlib.Path, required=True)
    parser.add_argument('--until-status', type=pathlib.Path, required=True)
    parser.add_argument('--cpu', type=int, default=6)
    parser.add_argument('--max-seconds', type=int, default=1800)
    parser.add_argument('--interval', type=int, default=5)
    args = parser.parse_args()
    assert not args.output.exists() and 1 <= args.interval <= 30
    assert 1 <= args.max_seconds <= 3600
    os.sched_setaffinity(0, {args.cpu})
    os.nice(max(0, 19 - os.getpriority(os.PRIO_PROCESS, 0)))
    frequency = os.sysconf('SC_CLK_TCK')
    started = previous_time = time.monotonic()
    previous = snapshot()
    result = dict(status='RUNNING', pid=os.getpid(), cpu=args.cpu, interval=args.interval,
                  started_ns=time.time_ns(), clock_ticks=frequency, samples=[],
                  limitation='Interval snapshots miss CPU from processes that start and exit between snapshots; no command-line arguments or process signals are used.')
    save(args.output, result)
    while time.monotonic() - started < args.max_seconds:
        time.sleep(args.interval)
        current_time = time.monotonic()
        current = snapshot()
        elapsed = current_time - previous_time
        consumers = []
        for key, (name, ticks) in current.items():
            if key in previous:
                delta = ticks - previous[key][1]
                if delta:
                    consumers.append(dict(pid=key[0], start_ticks=key[1], name=name,
                                          cpu_seconds=delta / frequency,
                                          one_core_percent=100 * delta / frequency / elapsed))
        consumers.sort(key=lambda x: x['cpu_seconds'], reverse=True)
        result['samples'].append(dict(realtime_ns=time.time_ns(), elapsed=elapsed,
                                      load=list(os.getloadavg()), consumers=consumers[:20]))
        previous, previous_time = current, current_time
        try:
            stage = json.loads(args.until_status.read_text())
        except FileNotFoundError:
            stage = {}
        status = stage.get('status', '')
        if status.startswith(('PASS', 'FAILED')):
            result.update(status='FINISHED_WITH_OBSERVED_STAGE', observed_status=status,
                          finished_ns=time.time_ns())
            save(args.output, result)
            break
        save(args.output, result)
    else:
        result.update(status='BOUNDED_OBSERVATION_ENDED', finished_ns=time.time_ns())
        save(args.output, result)
    print(json.dumps({k:v for k,v in result.items() if k != 'samples'}))


if __name__ == '__main__':
    main()
