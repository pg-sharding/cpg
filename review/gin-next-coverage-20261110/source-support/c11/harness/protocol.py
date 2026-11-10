import json
import pathlib

HERE = pathlib.Path(__file__).resolve().parent
BASE = '72b9498df9a369e747f8d96efb5a6cd33c2451e2'
SCREEN = {'skew1000','skew127','skew_group4096','inline','inline_single','jsonb','or_forced','single_rare','single_forced','dense_and','lossy_and','seq_control','absent'}


def sql_cases():
    return (json.loads((HERE / 'inputs/queries.json').read_text())['cases'] +
            json.loads((HERE / 'inputs/queries-holdout.json').read_text())['cases'])


def micro_cases():
    rows = [('am_inline', 'inline_d_gin', 'common & token17', 10000, 4),
            ('am_absent', 'docs_d_gin', 'common & missing', 5000, 0),
            ('am_skew1000', 'docs_d_gin', 'common & rare0', 100, 200),
            ('am_full', 'docs_d_gin', 'common', 10, 200000),
            ('am_or', 'docs_d_gin', 'common | rare0', 10, 200000),
            ('am_dense', 'docs_d_gin', 'dense2 & dense3', 10, 33333),
            ('am_rare', 'docs_d_gin', 'rare0', 1000, 200)]
    return [dict(name=name, kind='am', settings='', index=index, query=query,
                 loops=loops, tids_per_scan=tids,
                 sql=f"SELECT public.gin_am_micro('g1.{index}'::regclass, '{query}'::tsquery, {loops})")
            for name, index, query, loops, tids in rows]


def plan(mode):
    roles, retained = ['B','T','C9','C10','C11'], 10
    if mode == 'qualify':
        cases, cohorts = [], 0
    elif mode == 'screen':
        cases = [dict(c, kind='sql') for c in sql_cases() if c['name'] in SCREEN] + micro_cases()
        assert len(cases) == 20
        cohorts = 2
    else:
        assert mode == 'full'
        cases = [dict(c, kind='sql') for c in sql_cases()]
        assert len(cases) == 25
        cohorts = 2
    n = len(roles)
    base = [0,1,4,2,3]
    forward = [[roles[(x+k)%n] for x in base] for k in range(n)]
    orders = forward + [list(reversed(order)) for order in forward]
    assert len(orders) == retained
    return dict(mode=mode,roles=roles,retained_rounds=retained,warmups=2,cases=cases,orders=orders,cohorts=cohorts,
                raw=len(cases)*n*(retained+2)*cohorts,retained=len(cases)*n*retained*cohorts,warm=len(cases)*n*2*cohorts,
                timing='Separate SQL executor/whole-command CPU/client wall and real-AM loop process CPU/wall. B/T exact executable twins; no normalization. New independent campaign; old R1/R2 observations remain separate.')
