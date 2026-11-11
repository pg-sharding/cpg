"""Fixed D2 allocation-inclusive decoder and whole-SQL protocol; no result-dependent tuning."""
import collections,json,pathlib
HERE=pathlib.Path(__file__).resolve().parent
INPUTS=HERE.parent/'qualification/inputs'
BASE='72b9498df9a369e747f8d96efb5a6cd33c2451e2'
FIXED='8a8c475037bfde101da23cc9b0364c9c020eca93'
SQL_NAMES={'dense_and','single_forced','or_forced','single_rare','prefix','skew1000','seq_control'}

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

def sql_cases():
 return json.loads((INPUTS/'queries.json').read_text())['cases']+json.loads((INPUTS/'queries-holdout.json').read_text())['cases']

def plan():
 roles=['B','T','D1','D2'];base=[0,1,3,2]
 orders=[[roles[(x+k)%4]for x in base]for k in range(4)]*3
 assert collections.Counter((r,i)for order in orders for i,r in enumerate(order))==collections.Counter({(r,i):3 for r in roles for i in range(4)})
 assert collections.Counter((a,b)for order in orders for a,b in zip(order,order[1:]))==collections.Counter({(a,b):3 for a in roles for b in roles if a!=b})
 sql=[dict(c,kind='sql')for c in sql_cases()if c['name']in SQL_NAMES];assert len(sql)==7
 decoder=[dict(name='decode_'+name,decoder_case=name,kind='decoder',settings='',loops=loops,expected=decode_expected(n,shift,seg,first,loops),sql=f"SELECT public.gin_decoder_bench('{name}', {loops})")for name,n,shift,seg,first,loops in DECODE]
 cases=sql+decoder;assert len(cases)==len({c['name']for c in cases})==25
 return dict(roles=roles,cases=cases,orders=orders,warmups=2,retained_rounds=12,cohorts=2,raw=2800,retained=2400,warm=400,scope='7 wholeSQL +18 actualbackend allocation/materialization/free decoder cells; exact B/T; all6pairs and all negatives retained; no AM/fragment claim')

if __name__=='__main__':print(json.dumps(plan(),indent=2))
