#!/usr/bin/env python3
"""Offline review of one frozen 36-observation, zero-retained candidate smoke."""
import argparse
import hashlib
import json
import pathlib
import sys
import traceback

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / 'harness'))
from protocol import plan


def read(path):
    return json.loads(path.read_text())


def nodes(node):
    yield node
    for child in node.get('Plans', []):
        yield from nodes(child)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--collection', type=pathlib.Path)
    parser.add_argument('--output-new', type=pathlib.Path)
    parser.add_argument('--list-files', action='store_true')
    a = parser.parse_args()
    if a.list_files:
        files = ['status.json','protocol.json','frozen-inputs.json','module.json','seed-origin.json',
                 'seed-info.json','seed-manifest.json','qualification-summary.json','runtime-c0.json',
                 'cohort0/status.json','cohort0/raw.jsonl','cohort0/oracles.json']
        files += ['cohort0/' + role + '-backend.json' for role in plan('smoke')['roles']]
        print(json.dumps(files, indent=2))
        return
    assert a.collection is not None and a.output_new is not None
    a.output_new.mkdir()
    status = dict(status='RUNNING')
    try:
        spec = plan('smoke')
        assert len(spec['cases']) == 12 and len(spec['roles']) == 3
        assert (spec['raw'], spec['retained'], spec['warm'], spec['cohorts']) == (36, 0, 36, 1)
        outer = read(a.collection / 'status.json')
        assert outer['status'] == 'PASS' and outer['mode'] == 'smoke' and not outer['cleanup_errors']
        assert (outer['raw'], outer['retained'], outer['warm']) == (36, 0, 36)
        assert len(outer['clusters']) == 3 and all(x['stopped'] for x in outer['clusters'])
        assert all(outer[x] for x in ['full_source_unchanged', 'fixture_unchanged',
                    'installed_trees_unchanged', 'actual_am_module_unchanged', 'frozen_runtime_unchanged'])
        runtime = read(a.collection / 'runtime-c0.json')
        assert runtime['roles']['B']['prefix'] == runtime['roles']['T']['prefix']
        assert runtime['roles']['B']['backend_sha256'] == runtime['roles']['T']['backend_sha256']
        run = a.collection / 'cohort0'
        run_status = read(run / 'status.json')
        assert run_status['status'] == 'PASS' and not run_status['cleanup_errors']
        assert hashlib.sha256((run / 'raw.jsonl').read_bytes()).hexdigest() == run_status['raw_sha256']
        rows = [json.loads(x) for x in (run / 'raw.jsonl').read_bytes().splitlines()]
        assert len(rows) == 36 and not any(x['retained'] for x in rows)
        answers = read(HERE / 'harness/inputs/timing-answers.json')
        position = 0
        for case in spec['cases']:
            for i, role in enumerate(spec['roles']):
                row = rows[position]
                position += 1
                assert (row['case'], row['role'], row['cohort'], row['round'], row['position'], row['order']) == (
                        case['name'], role, 0, 0, i, spec['roles'])
                obs = row['observed']
                assert obs['client_ns'] > 0 and obs['command_delta']['cpu_ns'] > 0
                value = json.loads(obs['raw_result'])
                if case['kind'] == 'sql':
                    assert row['literal_answer'] == answers[case['name']]
                    tree = value[0]['Plan']
                    indexes = [x['Index Name'] for x in nodes(tree) if 'Index Name' in x]
                    assert (case['index'] in indexes) if case['index'] else not indexes
                    if case.get('require_lossy_heap'):
                        assert sum(x.get('Lossy Heap Blocks', 0) for x in nodes(tree)) > 0
                    if case.get('require_single_index_multiqual'):
                        assert any(x.get('Index Name') == case['index'] and x.get('Index Cond', '').count('&&') >= 2 for x in nodes(tree))
                else:
                    for native in [value, json.loads(row['literal_answer'])]:
                        assert native['loops'] == case['loops'] and native['total_tids'] == case['loops'] * case['tids_per_scan']
        assert read(run / 'oracles.json')['status'] == 'PASS'
        status.update(status='PASS_OFFLINE_ZERO_ACCEPTED_SMOKE_REVIEW', raw=36, retained=0,
                      stopped_clusters=3, raw_sha256=run_status['raw_sha256'],
                      scope='Offline review only; no benchmark launched by this reviewer.')
    except BaseException as exc:
        status.update(status='FAILED_PRESERVED', error=repr(exc), traceback=traceback.format_exc())
        raise
    finally:
        (a.output_new / 'status.json').write_text(json.dumps(status, indent=2) + '\n')
    print(json.dumps(status))


if __name__ == '__main__':
    main()
