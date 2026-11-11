#!/usr/bin/env python3
from pathlib import Path, PurePosixPath
import hashlib
import json
import subprocess
import sys
import tarfile

ROOT = Path(__file__).resolve().parent
assert str(ROOT) == '/home/reshke/wpgpg/ios14-199-1111'
data = (ROOT / 'inputs-r1.tar.gz').read_bytes()
receipt = json.loads((ROOT / 'INPUT-PREP-r1.json').read_text())
assert receipt['archive'] == dict(bytes=len(data), sha256=hashlib.sha256(data).hexdigest())
dest = ROOT / 'inputs-r1'
dest.mkdir()
seen = set()
with tarfile.open(ROOT / 'inputs-r1.tar.gz') as archive:
    for member in archive:
        name = PurePosixPath(member.name)
        assert not name.is_absolute() and '..' not in name.parts
        assert member.isfile() and member.name not in seen
        seen.add(member.name)
        p = dest / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(archive.extractfile(member).read())
        p.chmod(member.mode & 0o777)
manifest = json.loads((dest / 'INPUTS.json').read_text())
assert seen == set(manifest['files']) | {'INPUTS.json'}
for name, v in manifest['files'].items():
    b = (dest / name).read_bytes()
    assert v == dict(bytes=len(b), sha256=hashlib.sha256(b).hexdigest())
assert not (ROOT / 'PREPARE-r1.json').exists()
with (ROOT / 'prepare-controller-r1.log').open('xb') as log:
    p = subprocess.Popen([sys.executable, '-B', str(ROOT / 'run-prepare.py')], cwd=ROOT,
                         stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT,
                         start_new_session=True)
print(json.dumps(dict(status='QUEUED_AFTER_GIN', pid=p.pid)))
