#!/usr/bin/env python3
"""Local independent 92-row K3 smoke audit; never launches a server or timing."""
import argparse
import collections
import hashlib
import json
import math
import pathlib

HERE = pathlib.Path(__file__).resolve().parent
ROLES = ['B', 'T', 'K1', 'K3']
COMMITS = dict(B='8a8c475037bfde101da23cc9b0364c9c020eca93',
               T='8a8c475037bfde101da23cc9b0364c9c020eca93',
               K1='9e0d6e84c5bd538e58a534c99cb39ca669c567b7',
               K3='ec32d586cf3bb6cfa76eb672db70160b436ce47c')
GATE_SHA = '38ed88489dac9c2b01ee6ac4052bdc8860bbfa61062a5b3d86213f11e448bff3'
BUILD_SHA = '7afacbc4f8f9dbaed6cbd8a095c37b55b16737ac785701d42d0287953bc967f8'
AM = {'am_inline': (10000, 4), 'am_absent': (5000, 0),
      'am_skew1000': (100, 200), 'am_full': (10, 200000),
      'am_or': (10, 200000), 'am_dense': (10, 33333), 'am_rare': (1000, 200)}
FILES = ['timing-r1/' + n for n in
         ['prepare-status.json', 'smoke-status.json', 'freeze.json',
          'seed-inventory.json', 'runtime-smoke.json']]
FILES += ['timing-r1/smoke/' + n for n in
          ['status.json', 'raw.jsonl', 'literal.jsonl', 'oracles.json'] +
          [r + '-backend.json' for r in ROLES]]
FILES += ['qualification-r1/status.json', 'ROOT-LAUNCH-PREPARE-SMOKE-K3-r1.json',
          'timing-prepare-smoke-chain-r1.json']


def sha(p):
    return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()


def read(p):
    return json.loads(pathlib.Path(p).read_text())


def nodes(node):
    yield node
    for child in node.get('Plans', []):
        yield from nodes(child)


def signature(node):
    """Full tree, preserving planner/query and row/recheck/loop fields."""
    def keep(key):
        return not (key.endswith('Time') or key.endswith('Blocks') or
                    key.startswith(('I/O ', 'WAL ', 'Peak Memory', 'Sort Space')))
    return {k: ([signature(v) for v in value] if k == 'Plans' else value)
            for k, value in node.items() if keep(k)}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--list-files', action='store_true')
    p.add_argument('--collection', type=pathlib.Path)
    p.add_argument('--build-receipt', type=pathlib.Path,
                   default=HERE / 'evidence-r1/build-r1/build-receipt.json')
    p.add_argument('--out-new', type=pathlib.Path)
    a = p.parse_args()
    if a.list_files:
        print('\n'.join(FILES))
        return
    assert a.collection and a.out_new and not a.out_new.exists()
    c = a.collection
    for name in FILES:
        assert (c / name).is_file() and not (c / name).is_symlink(), name
    root = c / 'timing-r1'
    freeze = read(root / 'freeze.json')
    spec = read(HERE / 'timing-prep-r1/PROTOCOL.json')
    assert freeze['protocol'] == spec
    assert spec['roles'] == ROLES and len(spec['cases']) == 23
    assert (spec['raw'], spec['retained'], spec['warm']) == (2576, 2208, 368)
    # Reconstruct the declared Williams block independently of protocol.py.
    block = [[ROLES[(n + k) % 4] for n in [0, 1, 3, 2]] for k in range(4)]
    assert spec['orders'] == block * 3
    assert collections.Counter((r, i) for order in spec['orders'] for i, r in enumerate(order)) == collections.Counter({(r, i): 3 for r in ROLES for i in range(4)})
    assert collections.Counter((x, y) for order in spec['orders'] for x, y in zip(order, order[1:])) == collections.Counter({(x, y): 3 for x in ROLES for y in ROLES if x != y})
    for name, v in read(HERE / 'TIMING-INPUTS-K3-r1.json')['files'].items():
        assert sha(HERE / name) == v['sha256'] and (HERE / name).stat().st_size == v['bytes']
    for name, v in freeze['scripts'].items():
        path = HERE / name
        assert path.is_file() and sha(path) == v['sha256'] and path.stat().st_size == v['bytes'], name
    assert sha(a.build_receipt) == freeze['build_receipt_sha256'] == BUILD_SHA
    build = read(a.build_receipt)
    assert sha(c / 'qualification-r1/status.json') == freeze['qualification_sha256'] == GATE_SHA
    gate = read(c / 'qualification-r1/status.json')
    assert gate['status'] == 'PASS_ORDINARY_SQL_NATIVE_CACHE_BUDGET_AND_GENERIC_FALLBACK'
    assert gate['remaining_owned'] == gate['timing_samples'] == 0 and not gate['cleanup_errors']
    assert gate['build_receipt_sha256'] == BUILD_SHA
    assert sha(root / 'seed-inventory.json') == freeze['seed_inventory_sha256']
    assert len(freeze['copies']) == 12
    assert [v['rank'] for v in freeze['copies']] == list(range(12))
    assert len({v['path'] for v in freeze['copies']}) == 12
    assert max(v['fsync_end_ns'] for v in freeze['copies']) <= freeze['all_copies_fsync_done_ns']
    prepared = read(root / 'prepare-status.json')
    assert prepared['status'] == 'PASS_PREPARED_NO_TIMINGS' and prepared['copies'] == 12
    assert prepared['all_before_role_assignment'] and prepared['timing_samples'] == prepared['remaining_owned'] == 0
    assert not prepared['cleanup_errors'] and prepared['installed_source_inputs_unchanged']
    outer = read(root / 'smoke-status.json')
    assert outer['status'] == 'PASS_SMOKE_NEEDS_ROOT_REVIEW' and outer['timing_samples'] == 0
    assert outer['remaining_owned'] == 0 and not outer['cleanup_errors'] and outer['unused_accepted_copies'] == 8
    assert outer['installed_source_inputs_unchanged'] and len(outer['clusters']) == 4
    assert outer['environment_label'] == freeze['environment_label']
    assert freeze['all_copies_fsync_done_ns'] < outer['started_ns']
    for i, role in enumerate(ROLES):
        item = outer['clusters'][i]
        assert item['role'] == role and item['data'] == freeze['copies'][i]['path']
        assert item['port'] == freeze['first_port'] + i and item['stopped']
        assert item['stop_proof'] == dict(pg_ctl_status_rc=3, cluster_state='shut down', pidfile_absent=True)
    launch = read(c / 'ROOT-LAUNCH-PREPARE-SMOKE-K3-r1.json')
    chain = read(c / 'timing-prepare-smoke-chain-r1.json')
    assert launch['status'] == 'ROOT_REVIEWED_K3_PREPARE_SMOKE_ONLY_STARTED'
    assert launch['gate_status_sha256'] == GATE_SHA and launch['smoke_raw'] == 92
    assert launch['accepted_timing_samples'] == chain['accepted_timing_samples'] == 0
    assert chain['status'] == 'PASS_SMOKE_NEEDS_ROOT_REVIEW'
    run = root / 'smoke'
    status = read(run / 'status.json')
    assert status['status'] == 'PASS' and status['raw'] == 92 and status['retained'] == 0 and status['smoke_only']
    assert status['accepted_timing_samples'] == 0 and not status['cleanup_errors']
    assert sha(run / 'raw.jsonl') == status['raw_sha256'] and sha(run / 'literal.jsonl') == status['literal_sha256']
    rows = [json.loads(x) for x in (run / 'raw.jsonl').read_bytes().splitlines()]
    literals = [json.loads(x) for x in (run / 'literal.jsonl').read_bytes().splitlines()]
    assert len(rows) == len(literals) == 92
    answers = read(HERE / 'qualification/inputs/answers.json')
    counts = collections.Counter()
    previous_end = 0
    plans = {}
    position = 0
    for case in spec['cases']:
        for index, role in enumerate(block[0]):
            row, journal = rows[position], literals[position]
            position += 1
            assert (row['cohort'], row['case'], row['kind'], row['role'], row['round'], row['position'], row['order'], row['retained'], row['smoke_only']) == (0, case['name'], case['kind'], role, 0, index, block[0], False, True)
            assert (journal['case'], journal['kind'], journal['role'], journal['round'], journal['answer']) == (case['name'], case['kind'], role, 0, row['literal_answer'])
            obs = row['observed']
            assert previous_end < journal['realtime_ns'] <= obs['end_realtime_ns']
            previous_end = obs['end_realtime_ns']
            assert obs['client_ns'] > 0 and obs['command_delta']['cpu_ns'] > 0
            assert all(v >= 0 for v in obs['command_delta'].values())
            result = json.loads(obs['raw_result'])
            if case['kind'] == 'sql':
                assert row['literal_answer'] == answers[case['name']]
                plan = result[0]['Plan']
                assert (plan['Actual Rows'], plan['Actual Loops']) == (1, 1)
                indexes = [v for v in nodes(plan) if 'Index Name' in v]
                if case['index']:
                    assert indexes and all(v['Index Name'] == case['index'] and v['Actual Loops'] == case['probes'] for v in indexes)
                else:
                    assert not indexes
                    scans = [v for v in nodes(plan) if v['Node Type'] == 'Seq Scan']
                    assert scans and all(v['Actual Loops'] == case['probes'] for v in scans)
                assert math.isfinite(result[0]['Execution Time']) and result[0]['Execution Time'] > 0
                sig = signature(plan)
                if case['name'] in plans:
                    assert sig == plans[case['name']], ('plan signature', case['name'], role)
                plans[case['name']] = sig
            else:
                assert case['kind'] == 'am'
                loops, tids = AM[case['name']]
                assert (case['loops'], case['tids_per_scan']) == (loops, tids)
                for value in [result, json.loads(row['literal_answer'])]:
                    assert value['loops'] == loops and value['total_tids'] == loops * tids
                    assert value['cpu_ns'] > 0 and value['wall_ns'] > 0
            counts[case['kind']] += 1
    assert counts == dict(sql=64, am=28)
    oracle = read(run / 'oracles.json')
    assert oracle['status'] == 'PASS' and len(oracle['answers']) == 100
    names = {key.split('/', 1)[1] for key in oracle['answers']}
    assert len(names) == 25
    for name in names:
        base = oracle['answers']['B/' + name]
        for role in ROLES:
            v = oracle['answers'][role + '/' + name]
            assert v['reference_sha256'] == v['actual_sha256'] == base['actual_sha256'] and v['rows'] == base['rows']
    runtime = read(root / 'runtime-smoke.json')
    assert sha(root / 'runtime-smoke.json') == status['runtime_sha256']
    assert runtime['roles']['B']['prefix'] == runtime['roles']['T']['prefix']
    assert runtime['roles']['B']['backend_sha256'] == runtime['roles']['T']['backend_sha256']
    for role in ROLES:
        variant = 'B' if role == 'T' else role
        binding = runtime['roles'][role]
        assert binding['source_commit'] == COMMITS[role]
        assert binding['prefix'] == build['variants'][variant]['prefix']
        assert binding['backend_sha256'] == build['variants'][variant]['postgres_sha256']
        meta = read(run / (role + '-backend.json'))
        assert meta['clock'] == 'system' and meta['buffers'] == '512MB' and meta['assertions'] == 'off' and meta['local']
        assert meta['affinity'] == [runtime['server_cpu']] and meta['backend_sha256'] == binding['backend_sha256']
    receipt = dict(status='PASS_LOCAL_92_SMOKE_SEMANTICS_NEEDS_ROOT_LIVE_REVIEW',
                   raw=92, retained=0, accepted_timing_samples=0, cells=23,
                   SQL_observations=64, AM_observations=28, ordered_oracles=100,
                   same_full_tree_signatures=16, backend_bindings=4, stopped_clusters=4,
                   unused_accepted_copies_reported=8,
                   raw_sha256=sha(run / 'raw.jsonl'), literal_sha256=sha(run / 'literal.jsonl'),
                   freeze_sha256=sha(root / 'freeze.json'), smoke_status_sha256=sha(root / 'smoke-status.json'),
                   files={n: dict(bytes=(c / n).stat().st_size, sha256=sha(c / n)) for n in FILES},
                   external_live_checks='Root must separately verify actual PIDs/sockets absent and eight unused copies/source/prefix inventories unchanged.',
                   scope='Local audit of actual smoke evidence only. No latency conclusion or external timing approval generated.')
    a.out_new.write_text(json.dumps(receipt, indent=2) + '\n')
    print(json.dumps({k: v for k, v in receipt.items() if k != 'files'}))


if __name__ == '__main__':
    main()
