import json
import pathlib

HERE = pathlib.Path(__file__).resolve().parent
BASE = '72b9498df9a369e747f8d96efb5a6cd33c2451e2'
SCREEN = {'skew1000', 'or_forced', 'single_forced', 'inline', 'jsonb',
          'lossy_and', 'seq_control', 'skew_group4096', 'inline_single', 'absent'}


def sql_cases():
    return (json.loads((HERE / 'inputs/queries.json').read_text())['cases'] +
            json.loads((HERE / 'inputs/queries-holdout.json').read_text())['cases'])


def micro_cases():
    rows = [('am_inline', 'inline_d_gin', 'common & token17', 10000, 4),
            ('am_absent', 'docs_d_gin', 'common & missing', 5000, 0),
            ('am_skew1000', 'docs_d_gin', 'common & rare0', 100, 200),
            ('am_full', 'docs_d_gin', 'common', 10, 200000)]
    return [dict(name=name, kind='am', settings='', index=index, query=query,
                 loops=loops, tids_per_scan=tids,
                 sql=f"SELECT public.gin_am_micro('g1.{index}'::regclass, '{query}'::tsquery, {loops})")
            for name, index, query, loops, tids in rows]


def plan(mode):
    if mode == 'null':
        roles, retained = ['B', 'T', 'N2', 'N3', 'N4'], 20
        cases = [dict(c, kind='sql') for c in sql_cases() if c['name'] in {'inline', 'seq_control', 'absent'}]
        assert len(cases) == 3
    elif mode == 'screen':
        roles, retained = ['B', 'T', 'A4', 'L4', 'L7'], 20
        cases = [dict(c, kind='sql') for c in sql_cases() if c['name'] in SCREEN] + micro_cases()
        assert len(cases) == 14
    else:
        assert mode == 'full'
        roles, retained = ['B', 'T', 'L4', 'L7'], 12
        cases = [dict(c, kind='sql') for c in sql_cases()]
        assert len(cases) == 25
    n = len(roles)
    base = [0]
    for i in range(1, n):
        base.append((i + 1) // 2 if i % 2 else n - i // 2)
    orders = [[roles[(x + k) % n] for x in base] for k in range(n)]
    if n % 2:
        orders += [list(reversed(row)) for row in orders]
    assert retained % len(orders) == 0
    return dict(mode=mode, roles=roles, retained_rounds=retained, warmups=2,
                cases=cases, orders=orders, cohorts=2,
                raw=len(cases) * n * (retained + 2) * 2,
                retained=len(cases) * n * retained * 2,
                warm=len(cases) * n * 2 * 2,
                timing='SQL EXPLAIN executor, whole backend schedstat CPU and client wall; AM also has actual index_rescan/getbitmap loop process CPU and wall.')
