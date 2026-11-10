import json
import pathlib
HERE = pathlib.Path(__file__).resolve().parent
BASE = '72b9498df9a369e747f8d96efb5a6cd33c2451e2'
ROLES = ['B', 'T', 'Bitmap']

def sql_cases():
    original = json.loads((HERE / 'inputs/queries.json').read_text())['cases'] + json.loads((HERE / 'inputs/queries-holdout.json').read_text())['cases']
    return original + json.loads((HERE / 'inputs/timing-cases.json').read_text())['extra_sql']

def micro_cases():
    return [c for c in json.loads((HERE / 'inputs/timing-cases.json').read_text())['cases'] if c['kind'] == 'am']

def plan(mode):
    assert mode in ['smoke', 'screen']
    cases = json.loads((HERE / 'inputs/timing-cases.json').read_text())['cases']
    forward = [[ROLES[(i+k) % 3] for i in [0,1,2]] for k in range(3)]
    orders = forward + [list(reversed(x)) for x in forward]
    warm, retained, cohorts = (1,0,1) if mode == 'smoke' else (2,6,2)
    assert len(cases) == 12 and len(orders) == 6
    return dict(mode=mode,roles=ROLES,cases=cases,orders=orders,warmups=warm,retained_rounds=retained,cohorts=cohorts,
                raw=len(cases)*3*(warm+retained)*cohorts,retained=len(cases)*3*retained*cohorts,warm=len(cases)*3*warm*cohorts,
                timing='New independent candidate campaign; B/T exact ELF; keep cohorts/metrics/negatives separate, no trimming or normalization. Smoke has zero accepted samples; no automatic promotion.')
