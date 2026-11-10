"""Fail-closed acceptance and metric extraction for every warm/retained row."""
import json


def nodes(node):
    yield node
    for child in node.get('Plans', []):
        yield from nodes(child)


def validate(case, row, answers):
    observed = row['observed']
    result = json.loads(observed['raw_result'])
    assert observed['client_ns'] > 0 and observed['command_delta']['cpu_ns'] > 0
    assert all(v >= 0 for v in observed['command_delta'].values())
    metrics = dict(backend_cpu_ms=observed['command_delta']['cpu_ns'] / 1e6,
                   client_wall_ms=observed['client_ns'] / 1e6)
    if case['kind'] == 'sql':
        assert row['literal_answer'] == answers[case['name']]
        root = result[0]['Plan']
        assert root['Actual Rows'] == 1 and root['Actual Loops'] == 1
        indexes = [n for n in nodes(root) if 'Index Name' in n]
        if case['index']:
            selected = [n for n in indexes if n['Index Name'] == case['index']]
            assert selected and len(selected) == len(indexes)
            assert all(n['Actual Loops'] == case['probes'] for n in selected)
        else:
            assert not indexes
            scans = [n for n in nodes(root) if n['Node Type'] == 'Seq Scan']
            assert scans and all(n['Actual Loops'] == case['probes'] for n in scans)
        metrics['sql_execution_ms'] = result[0]['Execution Time']
    elif case['kind'] == 'am':
        for value in [json.loads(row['literal_answer']), result]:
            assert value['loops'] == case['loops']
            assert value['total_tids'] == case['loops'] * case['tids_per_scan']
            assert value['cpu_ns'] > 0 and value['wall_ns'] > 0
        metrics.update(am_loop_cpu_ms=result['cpu_ns'] / 1e6, am_loop_wall_ms=result['wall_ns'] / 1e6)
    else:
        assert case['kind'] == 'decoder'
        for value in [json.loads(row['literal_answer']), result]:
            assert value['name'] == case['decoder_case'] and value['loops'] == case['loops']
            for key, expected in case['expected'].items():
                assert value[key] == expected, (case['name'], key, value[key], expected)
            assert value['decoder_allocation_materialization_free_cpu_ms'] > 0
        metrics['decoder_allocation_materialization_free_cpu_ms'] = result['decoder_allocation_materialization_free_cpu_ms']
    assert all(value > 0 for value in metrics.values())
    return metrics
