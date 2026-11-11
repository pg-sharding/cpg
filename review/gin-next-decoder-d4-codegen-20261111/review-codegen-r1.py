#!/usr/bin/env python3
"""Offline text/receipt audit only; never invokes a compiler or backend."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import shlex


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path):
    return json.loads(path.read_text())


def body(path):
    text = path.read_text()
    return text[text.index('Disassembly of section'):]


def decoder(asm_path, nm_path):
    name = 'ginPostingListDecodeAllSegments'
    matches = [line.split() for line in nm_path.read_text().splitlines()
               if line.split()[-1] == name]
    assert len(matches) == 1
    start, size = (int(v, 16) for v in matches[0][:2])
    lines = re.search(r'^([0-9a-f]+) <' + name + r'>:\n(.*?)(?=\n[0-9a-f]+ <|\Z)',
                      asm_path.read_text(), re.M | re.S).group(2).splitlines()
    raw = bytearray()
    relocations = []
    instructions = []
    for line in lines:
        fields = line.split('\t')
        if len(fields) < 3:
            continue
        offset = int(fields[0].strip().rstrip(':'), 16)
        if offset >= start + size:
            continue
        encoded = bytes.fromhex(fields[1])
        assert offset == start + len(raw)
        raw.extend(encoded)
        instructions.append({'offset': offset - start, 'asm': fields[2].strip()})
        for at, kind, target in re.findall(r'([0-9a-f]+): (R_X86_64_\S+)\s+(\S+)', line):
            relocations.append({'offset': int(at, 16) - start, 'kind': kind, 'target': target})
    assert len(raw) == size
    return {'start': start, 'bytes': size, 'machine_bytes_sha256': hashlib.sha256(raw).hexdigest(),
            'relocations': relocations, 'instructions': instructions}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--prior', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    assert not args.output.exists()
    root, prior = args.root, args.prior
    inputs_root = root / 'root-codegen-r1'
    evidence = root / 'evidence-codegen-r1'
    inputs = load(inputs_root / 'INPUTS.json')
    status = load(evidence / 'status.json')
    assert status['status'] == 'PASS_FOUR_NORMAL_FULL_TU_CODEGEN'
    assert status['timing_samples'] == 0 and status['backend_or_link_execution'] is False
    assert status['headers_verified'] == 907 and status['old_headers_and_backend_unchanged'] is True
    assert len(load(inputs_root / 'headers.json')) == 907
    bindings = {}
    for name, binding in inputs['files'].items():
        path = inputs_root / name
        assert path.stat().st_size == binding['bytes'] and sha(path) == binding['sha256']
        bindings[name] = dict(binding)
    for name, value in [('cflags', inputs['cflags']), ('cppflags', inputs['cppflags'])]:
        assert (evidence / (name + '.txt')).read_text() == value
    assert sha(evidence / 'compiler.txt') == inputs['compiler_sha256']
    argv = load(inputs_root / 'ARGV.json')['args']
    prefix = inputs['prefix']
    assert argv[:-3] == ['gcc'] + shlex.split(inputs['cflags']) + shlex.split(inputs['cppflags']) + [
        '-I' + prefix + '/include/postgresql/server', '-I' + prefix + '/include', '-c']
    assert argv[-2] == '-o'
    files = ['cflags.txt', 'cppflags.txt', 'compiler.txt']
    for role in ['B', 'D2', 'D3', 'D4']:
        files += [role + '-compile.txt', role + '-normal-ASM.txt', role + '-normal-nm.txt']
    assert len(status['commands']) == len(files) == 15
    end = status['started_ns']
    for name, recorded in zip(files, status['commands']):
        assert load(evidence / (name + '.command.json')) == recorded
        assert recorded['returncode'] == 0 and sha(evidence / name) == recorded['stdout_sha256']
        assert end <= recorded['started_ns'] <= recorded['finished_ns']
        end = recorded['finished_ns']
    assert end <= status['finished_ns']
    roles = {}
    sizes = {'B': 589, 'D2': 844, 'D3': 1241, 'D4': 838}
    for role in sizes:
        source = inputs_root / (role + '.c')
        asm = evidence / (role + '-normal-ASM.txt')
        nm = evidence / (role + '-normal-nm.txt')
        role_status = status['roles'][role]
        assert sha(source) == role_status['source_sha256']
        assert sha(asm) == role_status['asm_sha256'] and sha(nm) == role_status['nm_sha256']
        compile_record = load(evidence / (role + '-compile.txt.command.json'))
        assert compile_record['args'] == argv and (evidence / (role + '-compile.txt')).read_bytes() == b''
        info = decoder(asm, nm)
        assert info['bytes'] == sizes[role]
        ins = info.pop('instructions')
        assert [x['asm'] for x in ins if x['asm'].startswith('push')] == [
            'push   %r15', 'push   %r14', 'push   %r13', 'push   %r12', 'push   %rbp', 'push   %rbx']
        assert sum(x['asm'] == 'sub    $0x18,%rsp' for x in ins) == 1
        assert not any('decode_varbyte' in x['asm'] or '%fs:' in x['asm'] for x in ins)
        info.update(source_sha256=sha(source), asm_sha256=sha(asm), nm_sha256=sha(nm),
                    local_stack_bytes=24, saved_register_bytes=48,
                    scalar_helper_symbol_or_reference=False,
                    stack_canary_in_decoder=False)
        if role != 'D4':
            old_asm, old_nm = prior / asm.name, prior / nm.name
            assert body(asm) == body(old_asm) and nm.read_bytes() == old_nm.read_bytes()
            info.update(all_function_bytes_and_relocations_equal_prior=True,
                        prior_asm_sha256=sha(old_asm), prior_nm_sha256=sha(old_nm),
                        normalized_full_disassembly_sha256=hashlib.sha256(body(asm).encode()).hexdigest())
        roles[role] = info
    assert sha(root / 'draft/src/backend/access/gin/ginpostinglist.c') == roles['D4']['source_sha256']
    assert all('decode_varbyte' not in (evidence / (role + '-normal-nm.txt')).read_text() for role in sizes)
    report = {'status': 'PASS_INDEPENDENT_TEXT_RECEIPT_AND_NORMAL_CODEGEN_REVIEW',
              'inputs_sha256': sha(inputs_root / 'INPUTS.json'),
              'status_sha256': sha(evidence / 'status.json'), 'bound_inputs': bindings,
              'commands_verified': 15, 'reported_header_count_verified': 907,
              'roles': roles, 'source_or_runtime_mutation': False,
              'D4_backend_qualification': 'NOT_RUN', 'D4_timing_samples': 0,
              'limits': ['Remote installed-header/backend before/after verification is attested by the reviewed runner and status, not repeated by this offline audit.',
                         'Relocatable objects were not collected; recorded object hashes cannot be independently recomputed from these text files.',
                         'Environment/system-header dependency closure is not fully captured.',
                         'No instruction-count, throughput, correctness qualification or causal performance conclusion follows from function size or code placement.']}
    args.output.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({'status': report['status'], 'commands': 15, 'function_bytes': sizes}))


if __name__ == '__main__':
    main()
