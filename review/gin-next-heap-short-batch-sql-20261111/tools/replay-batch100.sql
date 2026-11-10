\set ON_ERROR_STOP on
\pset pager off
\timing off
SET search_path=g1,public,pg_catalog;SET jit=off;SET max_parallel_workers_per_gather=0;
SET enable_memoize=off;SET gin_fuzzy_search_limit=0;SET work_mem='64MB';
SET statement_timeout='180s';SET lock_timeout='10s';
SELECT version(),pg_backend_pid();
\echo Independent100-rescan command illustration; psql Time is client elapsed, EXPLAIN Execution Time is executor time, no backend CPU metric.
\echo Require Actual Loops100 for docs/index in batch plans and1 for control; no per-probe normalization. All scan types are enabled. Preserve Seq and every actual natural plan; do not tune after observing it.
\timing off
\echo CASE sql_batch_or1
SET enable_seqscan=on;SET enable_bitmapscan=on;SET enable_indexscan=on;SET enable_indexonlyscan=on;SET enable_tidscan=on;SET work_mem='64MB';
SELECT count(*)=48 AND sum(id)=4816896 AS ok FROM (SELECT id FROM g1.docs WHERE d @@ 'group0'::tsquery) q
\gset fixture_
\if :fixture_ok
\else
\echo Frozen independent scalar answer does not match this fixture.
\quit 3
\endif
\timing on
SELECT sum(q.n),sum(q.s) FROM generate_series(1,100) p(i) CROSS JOIN LATERAL (SELECT count(*) n,sum(id) s FROM g1.docs WHERE d @@ 'group0'::tsquery OFFSET(p.i%1)) q;
EXPLAIN(ANALYZE,BUFFERS,WAL,TIMING OFF,FORMAT JSON) SELECT sum(q.n),sum(q.s) FROM generate_series(1,100) p(i) CROSS JOIN LATERAL (SELECT count(*) n,sum(id) s FROM g1.docs WHERE d @@ 'group0'::tsquery OFFSET(p.i%1)) q;
\timing off
\timing off
\echo CASE sql_batch_or2
SET enable_seqscan=on;SET enable_bitmapscan=on;SET enable_indexscan=on;SET enable_indexonlyscan=on;SET enable_tidscan=on;SET work_mem='64MB';
SELECT count(*)=97 AND sum(id)=9633841 AS ok FROM (SELECT id FROM g1.docs WHERE d @@ 'group0 | group1'::tsquery) q
\gset fixture_
\if :fixture_ok
\else
\echo Frozen independent scalar answer does not match this fixture.
\quit 3
\endif
\timing on
SELECT sum(q.n),sum(q.s) FROM generate_series(1,100) p(i) CROSS JOIN LATERAL (SELECT count(*) n,sum(id) s FROM g1.docs WHERE d @@ 'group0 | group1'::tsquery OFFSET(p.i%1)) q;
EXPLAIN(ANALYZE,BUFFERS,WAL,TIMING OFF,FORMAT JSON) SELECT sum(q.n),sum(q.s) FROM generate_series(1,100) p(i) CROSS JOIN LATERAL (SELECT count(*) n,sum(id) s FROM g1.docs WHERE d @@ 'group0 | group1'::tsquery OFFSET(p.i%1)) q;
\timing off
\timing off
\echo CASE sql_batch_or7
SET enable_seqscan=on;SET enable_bitmapscan=on;SET enable_indexscan=on;SET enable_indexonlyscan=on;SET enable_tidscan=on;SET work_mem='64MB';
SELECT count(*)=342 AND sum(id)=33719301 AS ok FROM (SELECT id FROM g1.docs WHERE d @@ 'group0 | group1 | group2 | group3 | group4 | group5 | group6'::tsquery) q
\gset fixture_
\if :fixture_ok
\else
\echo Frozen independent scalar answer does not match this fixture.
\quit 3
\endif
\timing on
SELECT sum(q.n),sum(q.s) FROM generate_series(1,100) p(i) CROSS JOIN LATERAL (SELECT count(*) n,sum(id) s FROM g1.docs WHERE d @@ 'group0 | group1 | group2 | group3 | group4 | group5 | group6'::tsquery OFFSET(p.i%1)) q;
EXPLAIN(ANALYZE,BUFFERS,WAL,TIMING OFF,FORMAT JSON) SELECT sum(q.n),sum(q.s) FROM generate_series(1,100) p(i) CROSS JOIN LATERAL (SELECT count(*) n,sum(id) s FROM g1.docs WHERE d @@ 'group0 | group1 | group2 | group3 | group4 | group5 | group6'::tsquery OFFSET(p.i%1)) q;
\timing off
\timing off
\echo CASE sql_batch_or8
SET enable_seqscan=on;SET enable_bitmapscan=on;SET enable_indexscan=on;SET enable_indexonlyscan=on;SET enable_tidscan=on;SET work_mem='64MB';
SELECT count(*)=391 AND sum(id)=38536540 AS ok FROM (SELECT id FROM g1.docs WHERE d @@ 'group0 | group1 | group2 | group3 | group4 | group5 | group6 | group7'::tsquery) q
\gset fixture_
\if :fixture_ok
\else
\echo Frozen independent scalar answer does not match this fixture.
\quit 3
\endif
\timing on
SELECT sum(q.n),sum(q.s) FROM generate_series(1,100) p(i) CROSS JOIN LATERAL (SELECT count(*) n,sum(id) s FROM g1.docs WHERE d @@ 'group0 | group1 | group2 | group3 | group4 | group5 | group6 | group7'::tsquery OFFSET(p.i%1)) q;
EXPLAIN(ANALYZE,BUFFERS,WAL,TIMING OFF,FORMAT JSON) SELECT sum(q.n),sum(q.s) FROM generate_series(1,100) p(i) CROSS JOIN LATERAL (SELECT count(*) n,sum(id) s FROM g1.docs WHERE d @@ 'group0 | group1 | group2 | group3 | group4 | group5 | group6 | group7'::tsquery OFFSET(p.i%1)) q;
\timing off
\timing off
\echo CASE seq_control
SET enable_seqscan=on;SET enable_bitmapscan=on;SET enable_indexscan=on;SET enable_indexonlyscan=on;SET enable_tidscan=on;SET work_mem='64MB';
SELECT count(*)=200000 AND sum(id)=20000100000 AS ok FROM (SELECT id FROM g1.docs WHERE id BETWEEN 1 AND 200000) q
\gset fixture_
\if :fixture_ok
\else
\echo Frozen independent scalar answer does not match this fixture.
\quit 3
\endif
\timing on
SELECT count(*),sum(id) FROM g1.docs WHERE id BETWEEN 1 AND 200000;
EXPLAIN(ANALYZE,BUFFERS,WAL,TIMING OFF,FORMAT JSON) SELECT count(*),sum(id) FROM g1.docs WHERE id BETWEEN 1 AND 200000;
\timing off
