"""Fixed small SQL-only continuation of the published Heap AM expressions."""
import collections
import json
import pathlib
HERE = pathlib.Path(__file__).resolve().parent
INPUTS = HERE
BASE = '72b9498df9a369e747f8d96efb5a6cd33c2451e2'
FIXED = '8a8c475037bfde101da23cc9b0364c9c020eca93'

def sql_cases():
    return json.loads((HERE / 'cases.json').read_text())['cases']

def plan():
    roles = ['B', 'T', 'Heap']
    forward = [[roles[(i+k) % 3] for i in [0,1,2]] for k in range(3)]
    orders = forward + [list(reversed(x)) for x in forward]
    assert collections.Counter((r,i) for order in orders for i,r in enumerate(order)) == collections.Counter({(r,i):2 for r in roles for i in range(3)})
    assert collections.Counter((a,b) for order in orders for a,b in zip(order,order[1:])) == collections.Counter({(a,b):2 for a in roles for b in roles if a!=b})
    cases = sql_cases()
    assert len(cases)==8 and all(c['kind']=='sql' for c in cases)
    assert [c['name'] for c in cases] == ['sql_or_dense'+str(n) for n in [1,2,7,8,32,128,512]] + ['seq_control']
    return dict(roles=roles,cases=cases,orders=orders,warmups=2,retained_rounds=6,
                cohorts=2,raw=384,retained=288,warm=96,
                scope='Eight SQL-only cells; unchanged old Heap source/ELFs/seed; no new AM or decoder timing; separate cohorts and all three pairs.')

if __name__=='__main__':
    print(json.dumps(plan(),indent=2))
