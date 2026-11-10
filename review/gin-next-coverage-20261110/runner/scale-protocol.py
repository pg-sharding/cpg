"""Fixed larger-fixture and empty-shared-buffer scopes; no global cache drop."""
ROLES = ['B', 'T', 'C9', 'C11']
VARIANTS = {'B': 'B', 'T': 'B', 'C9': 'C9', 'C11': 'C11'}
ORDERS = [[ROLES[(x+k) % 4] for x in [0, 1, 3, 2]] for k in range(4)]


def plan(mode):
    assert mode in ['warm', 'restart']
    rows = 1000000
    predicates = [('skew1000', "d @@ 'common & rare0'::tsquery", 1000, True),
                  ('skew127', "d @@ 'common & rare2'::tsquery", 127, True),
                  ('absent', "d @@ 'common & missing'::tsquery", 0, True),
                  ('full', "d @@ 'common'::tsquery", 1, True),
                  ('dense', "d @@ 'dense2 & dense3'::tsquery", 6, True),
                  ('or', "d @@ 'common | rare0'::tsquery", 1, True),
                  ('seq', 'id > 0', 1, False)]
    cases = []
    for name, predicate, divisor, indexed in predicates:
        count = rows // divisor if divisor else 0
        total = divisor * count * (count+1) // 2 if divisor else None
        cases.append(dict(name=name, predicate=predicate, indexed=indexed,
                          sql='SELECT count(*),sum(id) FROM g1.large_docs WHERE ' + predicate,
                          rows_sql='SELECT id FROM g1.large_docs WHERE ' + predicate + ' ORDER BY id',
                          answer=str(count)+'|'+(str(total) if total is not None else ''), count=count))
    if mode == 'restart':
        cases = [c for c in cases if c['name'] in ['skew1000', 'full', 'seq']]
    retained = 12 if mode == 'warm' else 4
    return dict(mode=mode, rows=rows, roles=ROLES, variants=VARIANTS, orders=ORDERS,
                cases=cases, cohorts=2, warmups=2, retained_rounds=retained,
                raw=len(cases)*4*(2+retained)*2, retained=len(cases)*4*retained*2,
                warm=len(cases)*4*2*2, shared_buffers='64MB', work_mem='64MB',
                cache_scope=('Warm OS cache and repeated queries; relation larger than shared buffers. '
                             'No claim that the whole target working set fits in shared buffers.' if mode == 'warm' else
                             'Owned postmaster restarted before EVERY measured query. Empty shared buffers, '
                             'OS cache warmed by copy/hash/qualification/prior runs. NOT cold disk or cold OS cache.'))
