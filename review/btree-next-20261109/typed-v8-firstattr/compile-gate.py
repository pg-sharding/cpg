#!/usr/bin/env python3
"""Compile complete pinned TUs against read-only, previously matched headers.

This is a code-generation gate, not a linked backend or SQL benchmark.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import subprocess

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--existing-root', type=Path, required=True)
p.add_argument('--out-new', type=Path, required=True)
a = p.parse_args()
ROOT = Path(__file__).resolve().parent
out = a.out_new.resolve()
out.mkdir(parents=True, exist_ok=False)
os.umask(0o077)
os.nice(max(0, 10 - os.getpriority(os.PRIO_PROCESS, 0)))
sha = lambda path: hashlib.sha256(Path(path).read_bytes()).hexdigest()
pins = json.loads((ROOT / 'SOURCE.json').read_text())
commands = []
receipt = {'scope': 'full-TU code generation only; no linked backend, runtime oracle or SQL timing',
           'status': 'RUNNING', 'commands': commands, 'builds': {}}

def capture(args):
    return subprocess.check_output(list(map(str, args)), text=True, stderr=subprocess.STDOUT)

def inventory(root):
    return {str(f.relative_to(root)): {'bytes': f.stat().st_size, 'sha256': sha(f)}
            for f in sorted(root.rglob('*')) if f.is_file() and not f.is_symlink()}

def blocks(assembly):
    found = {}
    for block in assembly.split('\n\n'):
        match = re.search(r'^[0-9a-f]+ <([^>]+)>:', block, re.M)
        if match:
            found[match[1]] = block
    return found

def normalized(block):
    # Normalize instruction addresses and local branch/call destinations, while
    # keeping opcodes/operands and relocation targets. No equality claim about
    # linked addresses or whole executables follows from this comparison.
    result = []
    for line in block.splitlines()[1:]:
        line = re.sub(r'^\s*[0-9a-f]+:\s*(?:[0-9a-f]{2} )+\s*', '', line)
        line = re.sub(r'\b[0-9a-f]+(?= <)', 'ADDR', line)
        line = re.sub(r'\b[0-9a-f]+(?=: R_X86_64_)', 'ADDR', line)
        line = re.sub(r'#\s*[0-9a-f]+', '# ADDR', line)
        result.append(line.strip())
    return '\n'.join(result)

try:
    compiler = capture(['gcc', '--version'])
    assert '13.3.0' in compiler
    receipt['compiler'] = compiler
    code = {}
    for mode, installed_role, binary_pin in [
        ('release', 'v6', '5dfbfc1bf3f25bf360b6d13b8dc40b579b9ecfcc61620249b3167a2b9f23facf'),
        ('assert', 'v7assert', '0440862d5ebc9353a770a6deca5cce61835881e983ef8b54b547d46594d1e4d0'),
    ]:
        prefix = a.existing_root / ('stage-' + installed_role) / str(a.existing_root / 'prefix').lstrip('/')
        binding = json.loads((a.existing_root / 'build-proof' / installed_role / 'binding.json').read_text())
        before = inventory(prefix)
        assert before == binding['installed_files']
        assert sha(prefix / 'bin/postgres') == binary_pin
        config = lambda name: capture([prefix / 'bin/pg_config', '--' + name]).strip()
        # DESTDIR installations report the compiled prefix, not their staging
        # root. Use the actual staged headers explicitly.
        includes = [prefix / 'include/postgresql/server', prefix / 'include/postgresql/internal']
        flags = shlex.split(config('cflags')) + shlex.split(config('cppflags'))
        assert '-O2' in flags and '-g' in flags
        assert ('#define USE_ASSERT_CHECKING 1' in (includes[0] / 'pg_config.h').read_text()) == (mode == 'assert')
        record = {'pg_config': str(prefix / 'bin/pg_config'), 'config': config('configure'),
                  'flags': flags, 'postgres_sha256': binary_pin, 'roles': {}}
        receipt['builds'][mode] = record
        code[mode] = {}
        current = out / 'nbtsearch.c'
        obj = out / 'nbtsearch.o'
        for role in ['V6', 'V6-twin', 'V8']:
            source = ROOT / 'source' / ('V6' if role == 'V6-twin' else role) / 'nbtsearch.c'
            assert sha(source) == pins['source_sha256']['V6' if role == 'V6-twin' else role]
            current.write_bytes(source.read_bytes())
            args = ['gcc', *flags, *('-I' + str(i) for i in includes), '-c', current, '-o', obj]
            q = subprocess.run(list(map(str, args)), capture_output=True, text=True, timeout=120)
            commands.append({'mode': mode, 'role': role, 'args': list(map(str, args)), 'rc': q.returncode})
            (out / (mode + '-' + role + '-compile.log')).write_text(q.stdout + q.stderr)
            assert q.returncode == 0, q.stderr
            assert not q.stderr.strip(), q.stderr
            kept = out / (mode + '-' + role + '.o')
            kept.write_bytes(obj.read_bytes())
            assembly = capture(['objdump', '-drw', obj])
            symbols = capture(['nm', '-S', '--defined-only', obj])
            (out / (mode + '-' + role + '.asm.txt')).write_text(assembly)
            (out / (mode + '-' + role + '.symbols.txt')).write_text(symbols)
            code[mode][role] = blocks(assembly)
            sizes = {}
            for line in symbols.splitlines():
                m = re.match(r'^[0-9a-f]+ ([0-9a-f]+) [tT] (.+)$', line)
                if m:
                    sizes[m[2]] = int(m[1], 16)
            record['roles'][role] = {'source_sha256': sha(source), 'object_sha256': sha(kept), 'sizes': sizes}
        assert record['roles']['V6']['object_sha256'] == record['roles']['V6-twin']['object_sha256']
        record['installed_files_before_after_equal'] = inventory(prefix) == before
        assert record['installed_files_before_after_equal']
        record['normalized_V6_V8_equal'] = {
            name: normalized(block) == normalized(code[mode]['V8'][name])
            for name, block in code[mode]['V6'].items() if name in code[mode]['V8']
        }
        helper = code[mode]['V8']['_bt_binsrch_int8_read']
        (out / (mode + '-V8-typed-helper.asm.txt')).write_text(helper + '\n')
        # In release the direct kernel must not call the general attribute
        # accessor. Assert builds also contain the unchanged generic oracle.
        if mode == 'release':
            assert 'nocache_index_getattr' not in helper
    receipt['status'] = 'PASS_FULL_TU_RELEASE_AND_ASSERT_EXACT_V6_TWINS'
except BaseException as e:
    receipt.update(status='FAIL', error=repr(e))
    raise
finally:
    (out / 'receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
print(receipt['status'])
