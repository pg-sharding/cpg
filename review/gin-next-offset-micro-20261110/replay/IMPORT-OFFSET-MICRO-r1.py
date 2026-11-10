#!/usr/bin/env python3
"""Import the one frozen public offset micro archive and launch compile only on leased VM158."""
import hashlib
import json
import os
import pathlib
import subprocess
import tarfile
import time

ROOT = pathlib.Path('/home/reshke/allfuzz/gin-next-c11-bitmap-20261110')
ARCHIVE_SHA = '50c7fcdd8537f175b44c92b2d1e16199dbce52ade84d399ebbfd877c84d39e40'
MANIFEST_SHA = '46390f82b742d5101ee8c0ee407e3809cb31b00503d4813d1e7f43143635febf'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    archive = ROOT / 'bitmap-offset-micro-inputs-r1.tar.gz'
    assert sha(archive) == ARCHIVE_SHA
    target = ROOT / 'offset-micro-inputs-r1'
    assert not target.exists() and not (ROOT / 'offset-micro-build-r1').exists()
    for name in ['bs-r1', 'os-r1', 'bt-r1', 'ot-r1']:
        status = json.loads((ROOT / name / 'status.json').read_text())
        assert status['status'] == 'PASS' and not status['cleanup_errors']
        assert all(x['stopped'] and not pathlib.Path('/proc', str(x['pid'])).exists()
                   for x in status['clusters'])
    for compiler in ['cc1', 'cc1plus']:
        assert subprocess.run(['pgrep', '-x', compiler], stdout=subprocess.DEVNULL).returncode == 1
    with tarfile.open(archive, 'r:gz') as stream:
        members = stream.getmembers()
        assert len(members) == 12
        assert len({m.name for m in members}) == 12
        for m in members:
            name = pathlib.PurePosixPath(m.name)
            assert m.isfile() and name.parts[0] == 'offset-micro-inputs-r1'
            assert not name.is_absolute() and '..' not in name.parts
            path = ROOT / name
            assert not path.exists()
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(stream.extractfile(m).read())
    manifest = target / 'MICRO-INPUTS-r1.json'
    assert sha(manifest) == MANIFEST_SHA
    files = json.loads(manifest.read_text())['files']
    assert {p.relative_to(target).as_posix() for p in target.rglob('*') if p.is_file()} == set(files) | {'MICRO-INPUTS-r1.json'}
    for name, value in files.items():
        path = target / name
        assert path.stat().st_size == value['bytes'] and sha(path) == value['sha256']
    pins = json.loads((target / 'EXTERNAL-BINDINGS.json').read_text())
    assert sha(ROOT / 'bitmap-build/build-receipt.json') == pins['build_receipt_sha256']
    assert sha(ROOT / 'bq-r1/status.json') == pins['qualification_status_sha256']
    args = ['nice', '-n', '10', 'python3', '-B', str(target / 'prepare-build.py'),
            '--build', str(ROOT / 'bitmap-build'), '--qualified-from', str(ROOT / 'bq-r1'),
            '--output-new', str(ROOT / 'offset-micro-build-r1')]
    with (ROOT / 'OFFSET-MICRO-COMPILE-LAUNCH-r1.log').open('xb') as stream:
        process = subprocess.Popen(args, stdin=subprocess.DEVNULL, stdout=stream,
                                   stderr=subprocess.STDOUT, start_new_session=True)
    receipt = dict(status='LAUNCHED_COMPILE_ONLY_NO_TIMING', args=args, pid=process.pid,
                   started_ns=time.time_ns(), load=list(os.getloadavg()),
                   archive_sha256=ARCHIVE_SHA, manifest_sha256=MANIFEST_SHA,
                   importer_sha256=sha(pathlib.Path(__file__).resolve()))
    (ROOT / 'OFFSET-MICRO-COMPILE-LAUNCH-r1.json').write_text(json.dumps(receipt, indent=2) + '\n')
    print(json.dumps(receipt))


if __name__ == '__main__':
    main()
