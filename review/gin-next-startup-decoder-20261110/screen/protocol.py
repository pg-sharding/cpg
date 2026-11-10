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
DECODE = [
    ('one', 1, -1, 1, False, 200000),
    ('tail1', 2, -1, 8, False, 200000),
    ('tail2', 3, -1, 8, False, 200000),
    ('tail3', 4, -1, 8, False, 200000),
    ('batch4', 5, -1, 8, False, 200000),
    ('batch5', 6, -1, 8, False, 200000),
    ('batch8', 9, -1, 16, False, 200000),
    ('dense128', 128, -1, 128, False, 20000),
    ('dense4096', 4096, -1, 4096, False, 2000),
    ('dense_multi', 4096, -1, 127, False, 1000),
    ('first_singleton_grow', 4096, -1, 511, True, 1000),
    ('singletons', 64, -1, 1, False, 20000),
    ('delta2', 128, 0, 128, False, 20000),
    ('delta3', 128, 7, 128, False, 20000),
    ('delta4', 128, 14, 128, False, 20000),
    ('delta5', 128, 21, 128, False, 20000),
    ('delta6', 128, 24, 128, False, 20000),
    ('delta7', 2, 31, 2, False, 200000),
]


def sql_cases():
    return (json.loads((INPUTS / 'queries.json').read_text())['cases'] +
            json.loads((INPUTS / 'queries-holdout.json').read_text())['cases'])


def decode_expected(n, shift, segment_items, first_singleton, loops):
    tids = [(i // 128, 1 + i % 128) if shift < 0 else (i << shift, 1) for i in range(n)]
    checksum = 1469598103934665603
    for block, offset in tids:
        checksum = ((checksum ^ block) * 1099511628211) % (1 << 64)
        checksum = ((checksum ^ offset) * 1099511628211) % (1 << 64)
    size, segments, pos = 0, 0, 0
    while pos < n:
        count = 1 if first_singleton and pos == 0 else min(segment_items, n - pos)
        values = [(block << 11) | offset for block, offset in tids[pos:pos + count]]
        encoded = sum(max(1, ((values[i] - values[i - 1]).bit_length() + 6) // 7) for i in range(1, len(values)))
        size += (8 + encoded + 1) // 2 * 2
        segments += 1
        pos += count
    return dict(items_per_loop=n, compressed_bytes=size, segments=segments,
                checksum=str(checksum), consumed=str(loops * (n + tids[0][0] + tids[-1][1])))


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
    roles = ['B', 'T', 'S1', 'D1', 'C9']
    base = [0, 1, 4, 2, 3]
    forward = [[roles[(x + k) % 5] for x in base] for k in range(5)]
    orders = forward + [list(reversed(order)) for order in forward]
    assert collections.Counter((r, i) for order in orders for i, r in enumerate(order)) == collections.Counter({(r, i): 2 for r in roles for i in range(5)})
    assert collections.Counter((a, b) for order in orders for a, b in zip(order, order[1:])) == collections.Counter({(a, b): 2 for a in roles for b in roles if a != b})
    sql = [dict(c, kind='sql') for c in sql_cases() if c['name'] in SQL_NAMES]
    assert len(sql) == 16
    decoder = [dict(name='decode_' + name, decoder_case=name, kind='decoder', settings='', loops=loops,
                    expected=decode_expected(n, shift, seg, first, loops),
                    sql=f"SELECT public.gin_decoder_bench('{name}', {loops})")
               for name, n, shift, seg, first, loops in DECODE]
    cases = sql + micro_cases() + decoder
    assert len(cases) == 41 and len({c['name'] for c in cases}) == 41
    return dict(roles=roles, cases=cases, orders=orders, warmups=2, retained_rounds=10,
                cohorts=2, raw=4920, retained=4100, warm=820,
                scope='16 SQL + 7 actual-AM + 18 actual-decoder cells; distinct metric boundaries, separate cohorts; all data retained')


if __name__ == '__main__':
    print(json.dumps(plan(), indent=2))
