#!/usr/bin/env python3
"""Compile four full translation units in a new scratch directory, without linking."""
import hashlib
import json
import os
from pathlib import Path
import resource
import shlex
import subprocess
import time

ROOT = Path(__file__).resolve().parent
OUT = ROOT / 'outputs-r1'
assert not OUT.exists()
OUT.mkdir()
os.nice(10)
resource.setrlimit(resource.RLIMIT_AS, (3000000000, 3000000000))


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


inputs = json.loads((ROOT / 'INPUTS.json').read_text())
for name, binding in inputs['files'].items():
    p = ROOT / name
    assert p.stat().st_size == binding['bytes'] and sha(p) == binding['sha256']
prefix = Path(inputs['prefix'])
headers = json.loads((ROOT / 'headers.json').read_text())


def check_prefix():
    inc = prefix / 'include/postgresql/server'
    actual = {str(p.relative_to(inc)): dict(bytes=p.stat().st_size, sha256=sha(p))
              for p in inc.rglob('*') if p.is_file()}
    assert actual == headers and len(actual) == 907
    assert sha(prefix / 'bin/postgres') == inputs['backend_sha256']


check_prefix()
receipt = dict(status='RUNNING_NORMAL_CODEGEN', started_ns=time.time_ns(),
               timing_samples=0, backend_or_link_execution=False, commands=[], roles={})


def run(name, args):
    started = time.time_ns()
    p = subprocess.run(args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=120)
    out = OUT / name
    out.write_bytes(p.stdout)
    record = dict(args=args, returncode=p.returncode, started_ns=started,
                  finished_ns=time.time_ns(), stdout_sha256=sha(out))
    receipt['commands'].append(record)
    (OUT / (name + '.command.json')).write_text(json.dumps(record, indent=2) + '\n')
    assert p.returncode == 0, (name, p.stdout.decode(errors='replace'))
    return p.stdout.decode()


try:
    cflags = run('cflags.txt', [str(prefix / 'bin/pg_config'), '--cflags'])
    cppflags = run('cppflags.txt', [str(prefix / 'bin/pg_config'), '--cppflags'])
    assert cflags == inputs['cflags'] and cppflags == inputs['cppflags']
    compiler = run('compiler.txt', ['gcc', '--version'])
    assert hashlib.sha256(compiler.encode()).hexdigest() == inputs['compiler_sha256']
    args = json.loads((ROOT / 'ARGV.json').read_text())['args']
    assert args[:-3] == ['gcc'] + shlex.split(cflags) + shlex.split(cppflags) + [
        '-I' + str(prefix / 'include/postgresql/server'), '-I' + str(prefix / 'include'), '-c']
    common = Path(args[-3]); obj = Path(args[-1])
    assert common.is_relative_to(ROOT) and obj.is_relative_to(ROOT)
    common.parent.mkdir(parents=True)
    for role in ['B', 'D2', 'D3', 'D4']:
        common.write_bytes((ROOT / (role + '.c')).read_bytes())
        run(role + '-compile.txt', args)
        run(role + '-normal-ASM.txt', ['objdump', '-drwC', str(obj)])
        run(role + '-normal-nm.txt', ['nm', '-S', '--size-sort', str(obj)])
        receipt['roles'][role] = dict(source_sha256=sha(common), object_sha256=sha(obj),
                                     asm_sha256=sha(OUT / (role + '-normal-ASM.txt')),
                                     nm_sha256=sha(OUT / (role + '-normal-nm.txt')))
    check_prefix()
    receipt.update(status='PASS_FOUR_NORMAL_FULL_TU_CODEGEN', headers_verified=907,
                   old_headers_and_backend_unchanged=True, finished_ns=time.time_ns())
except BaseException as error:
    receipt.update(status='FAILED_NORMAL_CODEGEN_PRESERVED', error=repr(error), finished_ns=time.time_ns())
    raise
finally:
    (OUT / 'status.json').write_text(json.dumps(receipt, indent=2) + '\n')
print(json.dumps({k:v for k,v in receipt.items() if k != 'commands'}))
