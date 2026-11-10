"""Prospective ordinary write/build controls; separate from scan measurements."""
ROLES = ['B', 'T', 'C9', 'C11']
VARIANTS = {'B': 'B', 'T': 'B', 'C9': 'C9', 'C11': 'C11'}
ORDERS = [[ROLES[(x + k) % 4] for x in [0, 1, 3, 2]] for k in range(4)]


def plan(operation):
    assert operation in ['create-index', 'insert', 'vacuum']
    relation = 'docs' if operation == 'create-index' else 'write_bench'
    return dict(operation=operation, roles=ROLES, variants=VARIANTS,
                cohorts=2, warmups=2, retained_rounds=12, orders=ORDERS,
                raw=112, retained=96, warm=16, relation=relation,
                queries=['common', 'common & rare0', 'dense3'],
                expected_rows={'create-index': [200000, 200, 66666],
                               'insert': [5000, 5, 1666],
                               'vacuum': [10000, 0, 3333]}[operation],
                expected_table_rows={'create-index': 200002, 'insert': 5000,
                                     'vacuum': 10000}[operation],
                command={'create-index': 'CREATE INDEX bench_idx ON g1.docs USING gin(d) WITH(fastupdate=off)',
                         'insert': 'INSERT INTO g1.write_bench SELECT id,d FROM g1.docs WHERE id BETWEEN 1 AND 5000 ORDER BY id',
                         'vacuum': 'VACUUM (INDEX_CLEANUP ON, TRUNCATE FALSE, PARALLEL 0) g1.write_bench'}[operation],
                scope='Warm cache, one owned cluster/backend active per command, normal durability; no cache dropping. DDL/reset/data preparation and correctness checks excluded from command timing. Independent campaign for each operation. No trimming, pooling, twin correction or normalization.')
