"""Prospective finite screen; no outcome-dependent case/round selection."""
import collections
import json
import pathlib

HERE = pathlib.Path(__file__).resolve().parent
INPUTS = HERE.parent / 'qualification/inputs'
BASE = '72b9498df9a369e747f8d96efb5a6cd33c2451e2'
FIXED = '8a8c475037bfde101da23cc9b0364c9c020eca93'
SQL_NAMES = {'skew1000', 'skew127', 'skew_group4096', 'inline', 'inline_single',
             'jsonb', 'or_forced', 'single_rare', 'single_forced', 'dense_and',
             'lossy_and', 'seq_control', 'absent', 'prefix', 'phrase', 'not'}

def sql_cases():
    return (json.loads((INPUTS / 'queries.json').read_text())['cases'] +
            json.loads((INPUTS / 'queries-holdout.json').read_text())['cases'])


def micro_cases():
    rows = [('am_inline', 'inline_d_gin', 'common & token17', 10000, 4),
            ('am_absent', 'docs_d_gin', 'common & missing', 5000, 0),
            ('am_skew1000', 'docs_d_gin', 'common & rare0', 100, 200),
            ('am_full', 'docs_d_gin', 'common', 10, 200000),
            ('am_or', 'docs_d_gin', 'common | rare0', 10, 200000),
            ('am_dense', 'docs_d_gin', 'dense2 & dense3', 10, 33333),
            ('am_rare', 'docs_d_gin', 'rare0', 1000, 200)]
    return [dict(name=name, kind='am', settings='', index=index, query=query, loops=loops,
                 tids_per_scan=tids,
                 sql=f"SELECT public.gin_am_micro('g1.{index}'::regclass, '{query}'::tsquery, {loops})")
            for name, index, query, loops, tids in rows]


def plan():
    roles = ['B', 'T', 'K1', 'K3']
    base = [0, 1, 3, 2]
    block = [[roles[(x + k) % 4] for x in base] for k in range(4)]
    orders = block * 3
    assert collections.Counter((r, i) for order in orders for i, r in enumerate(order)) == collections.Counter({(r, i): 3 for r in roles for i in range(4)})
    assert collections.Counter((a, b) for order in orders for a, b in zip(order, order[1:])) == collections.Counter({(a, b): 3 for a in roles for b in roles if a != b})
    sql = [dict(c, kind='sql') for c in sql_cases() if c['name'] in SQL_NAMES]
    assert len(sql) == 16
    cases = sql + micro_cases()
    assert len(cases) == 23 and len({c['name'] for c in cases}) == 23
    return dict(roles=roles, cases=cases, orders=orders, warmups=2, retained_rounds=12,
                cohorts=2, raw=2576, retained=2208, warm=368,
                scope='16 SQL + 7 actual-AM cells; no decoder claim; separate cohorts and all six pairs retained')


if __name__ == '__main__':
    print(json.dumps(plan(), indent=2))
