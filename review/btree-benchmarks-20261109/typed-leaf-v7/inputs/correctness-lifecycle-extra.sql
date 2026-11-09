-- Prospective V7 correctness input; NOT RUN in this source-only follow-up.
-- Execute on NEW own correctness clusters with B/V6/V7/assert; compare output.
\set ON_ERROR_STOP on
\pset format unaligned
\pset tuples_only on
SET jit=off;
SET max_parallel_workers_per_gather=0;
SET enable_seqscan=off;
SET enable_bitmapscan=off;
CREATE TABLE leaf_empty(k bigint);
CREATE INDEX leaf_empty_idx ON leaf_empty(k);
BEGIN ISOLATION LEVEL SERIALIZABLE;
SELECT count(*) FROM leaf_empty WHERE k>=0::bigint;
COMMIT;
INSERT INTO leaf_empty VALUES(-1),(0),(1),(NULL);
SELECT array_agg(k ORDER BY k) FROM leaf_empty WHERE k>=0::bigint;
TRUNCATE leaf_empty;
BEGIN ISOLATION LEVEL SERIALIZABLE;
SELECT count(*) FROM leaf_empty WHERE k<=0::bigint;
COMMIT;
INSERT INTO leaf_empty SELECT (g%7)::bigint FROM generate_series(1,2000)g;
VACUUM(ANALYZE)leaf_empty;
REINDEX INDEX leaf_empty_idx;
SELECT k,count(*) FROM leaf_empty GROUP BY k ORDER BY k;
BEGIN;
DECLARE leaf_cursor SCROLL CURSOR FOR SELECT k FROM leaf_empty WHERE k>=2::bigint AND k<=4::bigint ORDER BY k;
FETCH FORWARD 3 FROM leaf_cursor;
MOVE FORWARD 20 FROM leaf_cursor;
FETCH BACKWARD 4 FROM leaf_cursor;
MOVE ABSOLUTE 1 FROM leaf_cursor;
FETCH FORWARD 3 FROM leaf_cursor;
ROLLBACK;
CREATE DOMAIN leaf_domain AS bigint;
CREATE TABLE leaf_domain_table(k leaf_domain);
INSERT INTO leaf_domain_table VALUES('-9223372036854775808'),(-1),(0),(1),('9223372036854775807'),(NULL);
CREATE INDEX leaf_domain_idx ON leaf_domain_table(k);
SELECT k FROM leaf_domain_table WHERE k>=0::leaf_domain ORDER BY k DESC;
SELECT count(*) FROM leaf_domain_table WHERE k=1::int2;
SELECT bt_index_parent_check('leaf_empty_idx',true,true);
SELECT bt_index_parent_check('leaf_domain_idx',true,true);
SELECT 'leaf-lifecycle-extra:ok';
