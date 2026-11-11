#!/usr/bin/env python3
"""Verify transferred inputs and start the fixed, finite build on the new VM."""
from pathlib import Path, PurePosixPath
import ast
import hashlib
import json
import os
import subprocess
import tarfile
import time

ROOT = Path(__file__).resolve().parent
assert str(ROOT) == '/home/reshke/c9-199-1111'
receipt = json.loads((ROOT / 'INPUT-PREP-r1.json').read_text())
for name, bound in receipt['archives'].items():
    data = (ROOT / name).read_bytes()
    assert bound == {'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}
inputs = ROOT / 'inputs-r1'
inputs.mkdir()
with tarfile.open(ROOT / 'inputs-r1.tar.gz', 'r:gz') as tar:
    seen = set()
    for member in tar:
        name = PurePosixPath(member.name)
        assert not name.is_absolute() and '..' not in name.parts
        assert member.isfile() and member.name not in seen
        seen.add(member.name)
        dest = inputs / name
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(tar.extractfile(member).read())
        dest.chmod(member.mode & 0o777)
manifest = json.loads((inputs / 'INPUTS.json').read_text())
assert seen == set(manifest['files']) | {'INPUTS.json'}
for name, bound in manifest['files'].items():
    p = inputs / name
    data = p.read_bytes()
    assert bound == {'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}
    if p.suffix == '.py':
        ast.parse(p.read_text())

def capture(*args):
    return subprocess.check_output(args, text=True).strip()

topology = capture('lscpu', '-p=CPU,CORE,SOCKET')
cores = {int(s[0]): (int(s[1]), int(s[2]))
         for line in topology.splitlines() if not line.startswith('#')
         for s in [line.split(',')]}
assert cores[0] != cores[4] and {0, 4} <= os.sched_getaffinity(0)
host = {'utc_ns': time.time_ns(), 'uname': list(os.uname()),
        'cpu': json.loads(capture('lscpu', '-J')), 'topology': topology,
        'affinity': sorted(os.sched_getaffinity(0)),
        'memory': Path('/proc/meminfo').read_text(),
        'load': list(os.getloadavg()),
        'compiler': capture('gcc', '--version'),
        'packages': capture('dpkg-query', '-W', 'gcc', 'gcc-13', 'make', 'flex',
                            'bison', 'libssl-dev', 'zlib1g-dev', 'libc6', 'python3'),
        'base_archive': receipt['archives']['baseline-B72.tar.gz'],
        'input_manifest_sha256': hashlib.sha256((inputs / 'INPUTS.json').read_bytes()).hexdigest()}
(ROOT / 'HOST-BUILD-r1.json').write_text(json.dumps(host, indent=2) + '\n')

driver = inputs / 'followup-r3/build-harness/build.py'
args = ['python3', '-B', str(driver), '--source-archive', str(ROOT / 'baseline-B72.tar.gz'),
        '--source-plan', str(inputs / 'followup-r3/build-source/SOURCE.json'),
        '--output', str(ROOT / 'build-r1'), '--core-port', '44740']
assert not (ROOT / 'build-r1').exists()
with (ROOT / 'build-controller-r1.log').open('xb') as log:
    proc = subprocess.Popen(args, cwd=ROOT, stdin=subprocess.DEVNULL,
                            stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
launch = {'status': 'BUILD_LAUNCHED', 'pid': proc.pid, 'argv': args,
          'launched_ns': time.time_ns(), 'host': '51.250.5.199',
          'input_manifest_sha256': host['input_manifest_sha256']}
(ROOT / 'BUILD-LAUNCH-r1.json').write_text(json.dumps(launch, indent=2) + '\n')
print(json.dumps(launch))
