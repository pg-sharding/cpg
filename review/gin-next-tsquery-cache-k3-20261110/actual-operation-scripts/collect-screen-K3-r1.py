#!/usr/bin/env python3
"""Collect selected text only after the accepted run and all eight stops PASS."""
import argparse
import hashlib
import importlib.util
import json
import pathlib
import shlex
import shutil
import subprocess
import time

HERE = pathlib.Path(__file__).resolve().parent
REMOTE = '/home/reshke/allfuzz/gin-cache-k3-20261110'
HOST = 'reshke@158.160.212.50'
NEW_FILES = ['timing-r1/run-status.json', 'timing-r1/runtime-cohort0.json',
             'timing-r1/runtime-cohort1.json', 'ROOT-LAUNCH-ACCEPTED-K3-r1.json',
             'ROOT-SMOKE-REVIEW-K3-r1.json']
for cohort in [0, 1]:
    NEW_FILES += [f'timing-r1/cohort{cohort}/' + name for name in
                  ['status.json', 'raw.jsonl', 'literal.jsonl', 'oracles.json'] +
                  [r + '-backend.json' for r in ['B', 'T', 'K1', 'K3']]]


def sha(p):
    return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--list-files', action='store_true')
    parser.add_argument('--out-new', type=pathlib.Path, default=HERE / 'screen-collected-r1')
    a = parser.parse_args()
    if a.list_files:
        print('\n'.join(NEW_FILES))
        return
    a.out_new.mkdir()
    receipt = dict(status='COLLECTING_AFTER_PASS', started_ns=time.time_ns(),
                   remote_root=REMOTE, commands=[],
                   excludes=['PGDATA', 'executables', 'shared objects', 'full runner/server logs'])
    def invoke(command, timeout=45):
        result = subprocess.run(command, text=True, capture_output=True, timeout=timeout)
        receipt['commands'].append(dict(args=command, returncode=result.returncode, stderr=result.stderr))
        assert result.returncode == 0, result.stderr
        return result.stdout
    try:
        # Only a small completed status is read before the post-run transfer.
        command = ['/usr/bin/ssh', '-A', '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=10', HOST,
                   'cat -- ' + shlex.quote(REMOTE + '/timing-r1/run-status.json')]
        status = json.loads(invoke(command))
        assert status['status'] == 'PASS_FIXED_SCREEN'
        assert (status['raw'], status['retained'], status['warm']) == (2576, 2208, 368)
        assert status['remaining_owned'] == 0 and not status['cleanup_errors'] and len(status['clusters']) == 8
        assert all(v['stopped'] for v in status['clusters'])
        smoke = HERE / 'smoke-collected-r1'
        old = json.loads((smoke / 'COLLECTION.json').read_text())
        assert old['status'] == 'PASS_EXACT_READ_ONLY_16_FILE_COLLECTION'
        for name, value in old['files'].items():
            source = smoke / name
            assert sha(source) == value['sha256'] and source.stat().st_size == value['bytes']
            target = a.out_new / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, target)
        shutil.copyfile(smoke / 'COLLECTION.json', a.out_new / 'SMOKE-COLLECTION.json')
        groups = {}
        for name in NEW_FILES:
            p = pathlib.PurePosixPath(name)
            groups.setdefault(str(p.parent), []).append(p.name)
        for folder, names in groups.items():
            target = a.out_new / folder
            target.mkdir(parents=True, exist_ok=True)
            sources = [HOST + ':' + REMOTE + '/' + (folder + '/' if folder != '.' else '') + n for n in names]
            invoke(['/usr/bin/scp', '-A', '-q', '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=10', *sources, str(target)], 90)
        names = sorted(set(old['files']) | set(NEW_FILES))
        assert len(names) == 37
        text = invoke(['/usr/bin/ssh', '-A', '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=10', HOST,
                       'sha256sum -- ' + ' '.join(shlex.quote(REMOTE + '/' + n) for n in names)], 90)
        remote = {line.split(None, 1)[1].strip().removeprefix(REMOTE + '/'): line.split(None, 1)[0]
                  for line in text.splitlines()}
        assert set(remote) == set(names)
        files = {}
        for name in names:
            p = a.out_new / name
            assert sha(p) == remote[name], name
            files[name] = dict(bytes=p.stat().st_size, sha256=sha(p))
        receipt.update(status='PASS_EXACT_37_TEXT_FILES_AFTER_ACCEPTED_RUN_AND_STOPS',
                       files=files, remote_hashes_checked=True, prior_smoke_files=16, new_files=21,
                       raw=2576, retained=2208, warm=368)
    except BaseException as exc:
        receipt.update(status='FAILED_PRESERVED_NO_RETRY', error=repr(exc))
        raise
    finally:
        receipt['finished_ns'] = time.time_ns()
        (a.out_new / 'COLLECTION.json').write_text(json.dumps(receipt, indent=2) + '\n')
    print(json.dumps({k: v for k, v in receipt.items() if k not in ['commands', 'files']}))


if __name__ == '__main__':
    main()
