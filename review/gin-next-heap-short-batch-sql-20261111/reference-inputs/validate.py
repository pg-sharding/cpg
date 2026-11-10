"""Validate complete natural-plan SQL results without requiring a common plan."""
import json
import math

SCAN_SETTINGS = ['enable_seqscan', 'enable_bitmapscan', 'enable_indexscan', 'enable_indexonlyscan', 'enable_tidscan']


def nodes(node):
    yield node
    for child in node.get('Plans', []):
        yield from nodes(child)


def natural_plan(case, root, executed):
    found = list(nodes(root))
    indexes = [n for n in found if 'Index Name' in n]
    permitted = {'docs_d_gin', 'docs_pkey'} if case['index'] else {'docs_pkey'}
    assert all(n['Index Name'] in permitted for n in indexes)
    scans = [n for n in found if n.get('Relation Name') == 'docs' and n['Node Type'] in {'Seq Scan', 'Bitmap Heap Scan', 'Index Scan', 'Index Only Scan', 'Tid Scan', 'Tid Range Scan'}]
    assert len(scans) == 1
    if executed:
        assert case['expected_count'] == case['per_scan_rows']
        assert case['output_count'] == case['probes'] * case['per_scan_rows']
        assert case['output_sum'] == case['probes'] * case['per_scan_sum']
        assert root['Actual Rows'] == root['Actual Loops'] == 1
        assert scans[0]['Actual Rows'] == case['expected_count'] and scans[0]['Actual Loops'] == case['probes']
        assert all(n['Actual Loops'] == case['probes'] for n in indexes)
    return found


def validate(case, row, answers):
    assert case['kind'] == 'sql' and case['plan_policy'] == 'NATURAL_ANY_VALID_PATH'
    assert row['literal_answer'] == answers[case['name']] == case['answer']
    settings = row['planner_settings']
    assert set(settings) == set(SCAN_SETTINGS + ['work_mem'])
    assert all(settings[k] == 'on' for k in SCAN_SETTINGS) and settings['work_mem'] == '64MB'
    observed = row['observed']
    assert observed['client_ns'] > 0 and observed['command_delta']['cpu_ns'] > 0
    assert all(v >= 0 for v in observed['command_delta'].values())
    result = json.loads(observed['raw_result'])
    assert len(result) == 1
    natural_plan(case, result[0]['Plan'], True)
    metrics = dict(backend_cpu_ms=observed['command_delta']['cpu_ns'] / 1e6,
                   client_wall_ms=observed['client_ns'] / 1e6,
                   sql_execution_ms=result[0]['Execution Time'])
    assert all(math.isfinite(v) and v > 0 for v in metrics.values())
    return metrics
