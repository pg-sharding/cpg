#!/usr/bin/env python3
"""Inspect collected normal decoder ASM locally; no compiler, binary loading or timing."""
import argparse
import hashlib
import json
import pathlib
import re
import time

HERE = pathlib.Path(__file__).resolve().parent
FUNCTION = 'ginPostingListDecodeAllSegments'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def parse(text):
    match = re.search(r'^([0-9a-f]+) <' + FUNCTION + r'>:\n', text, re.M)
    assert match
    start = int(match[1], 16)
    block = re.split(r'\n[0-9a-f]+ <', text[match.end():], 1)[0]
    rows = []
    for line in block.splitlines():
        instruction = re.match(r'\s*([0-9a-f]+):\t([0-9a-f ]+)\t(.*)', line)
        if instruction:
            rows.append(dict(address=int(instruction[1], 16),
                             bytes=bytes.fromhex(instruction[2]), assembly=instruction[3]))
    # objdump prints alignment after a symbol. Exclude trailing padding, retaining
    # all internal alignment and all cold scalar tails within the function.
    while rows[-1]['assembly'].startswith(('nop', 'data16', 'cs nop')):
        rows.pop()
    assert rows[0]['address'] == start
    assert all(a['address'] + len(a['bytes']) == b['address'] for a, b in zip(rows, rows[1:]))
    return rows, start, b''.join(row['bytes'] for row in rows)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--evidence', type=pathlib.Path, required=True)
    parser.add_argument('--output', type=pathlib.Path, required=True)
    args = parser.parse_args()
    assert not args.output.exists()
    build = args.evidence / 'build-r1'
    receipt = json.loads((build / 'build-receipt.json').read_text())
    codegen = json.loads((HERE / 'evidence-codegen-r2/status.json').read_text())
    out = dict(status='RUNNING_LOCAL_NORMAL_ASM_REVIEW', reviewed_ns=time.time_ns(), timing_samples=0)
    try:
        roles = {}
        for role, expected_size in [('B', 589), ('D2', 844), ('D3', 1241)]:
            path = build / f'{role}-ginpostinglist-normal-ASM.txt'
            source = path.read_text()
            binding = receipt['variants'][role]['normal_objects']['ginpostinglist']
            assert sha(path) == binding['asm_sha256']
            assert json.loads((build / f'{role}-backend-objects.json').read_text())['access/gin/ginpostinglist.o']['sha256'] == binding['object_sha256']
            assert 'decode_varbyte' not in source
            rows, start, machine = parse(source)
            prior = HERE / 'evidence-codegen-r2' / f'{role}-normal-ASM.txt'
            assert sha(prior) == codegen['roles'][role]['asm_sha256']
            prior_rows, prior_start, prior_machine = parse(prior.read_text())
            assert start == prior_start and machine == prior_machine
            assert [row['assembly'] for row in rows] == [row['assembly'] for row in prior_rows]
            assert len(machine) == expected_size
            pushes = [row['assembly'].split()[-1] for row in rows if row['assembly'].startswith('push')]
            assert pushes == ['%r15', '%r14', '%r13', '%r12', '%rbp', '%rbx']
            adjustments = [row['assembly'] for row in rows if re.match(r'(sub|add)\s+\$.*,%rsp$', row['assembly'])]
            assert adjustments == ['sub    $0x18,%rsp', 'add    $0x18,%rsp']
            assert not any('%fs:' in row['assembly'] or '__stack_chk_fail' in row['assembly'] for row in rows)
            calls = [dict(address=hex(row['address']), target=row['assembly'].split('\t')[-1].removesuffix('-0x4'))
                     for row in rows if row['assembly'].startswith('call')]
            assert [call['target'] for call in calls] == ['palloc_mul'] + ['repalloc_mul'] * (3 if role == 'D3' else 2)
            roles[role] = dict(asm_sha256=sha(path), object_sha256=binding['object_sha256'],
                               function_bytes=len(machine), machine_bytes_sha256=hashlib.sha256(machine).hexdigest(),
                               function_bytes_match_reviewed_r2_compile=True, helper_symbol_or_call=False,
                               local_rsp_bytes=24, saved_registers=pushes, saved_register_bytes=48,
                               additional_stack_bytes_excluding_incoming_return_address=72,
                               stack_canary_in_this_function=False, static_call_sites=calls)
        d3 = (build / 'D3-ginpostinglist-normal-ASM.txt').read_text()
        assert all(fragment in d3 for fragment in ['cmp    $0x3,%ax', 'or     0xb(%r15),%dl',
                                                   'js     3b0 <', 'jns    4f0 <'])
        out.update(status='PASS_ACTUAL_RELEASE_NORMAL_ASM_REVIEW', roles=roles,
                   build_receipt_sha256=sha(build / 'build-receipt.json'),
                   observation='D3 segment classification and separate scalar/batch paths remain. Machine bytes match the reviewed normal r2 compile exactly.',
                   negatives=['D3 is397bytes/+47.04% larger than D2 and652bytes/+110.70% larger than B.',
                              'D3 duplicates one growth-call site, not evidence of extra runtime allocation calls.',
                              'Early multi-byte deltas select scalar for the whole segment and can lose later batch gains; initially dense segments retain later D2 dispatch costs.',
                              'No latency result or causal performance conclusion follows from this static review.'],
                   assert_build_scope='Excluded from release normal-codegen comparisons; different flags.',
                   finished_ns=time.time_ns())
    except BaseException as exc:
        out.update(status='FAILED_LOCAL_ASM_AUDIT_PRESERVED', error=repr(exc))
        raise
    finally:
        args.output.write_text(json.dumps(out, indent=2) + '\n')
    print(json.dumps(out))


if __name__ == '__main__':
    main()
