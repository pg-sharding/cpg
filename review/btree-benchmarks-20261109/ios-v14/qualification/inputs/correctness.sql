\set ON_ERROR_STOP on
SET client_min_messages=warning;
SET jit=off;
SET statement_timeout='30s';
SET max_parallel_workers_per_gather=0;
DROP TABLE IF EXISTS corr;
CREATE TABLE corr AS
SELECT g, repeat((g%200)::text,1+(g%200)%7) COLLATE "C" AS a,
 CASE WHEN (g%200)%5=0 THEN NULL ELSE repeat((g%200)::text,1+(g%200)%11) END COLLATE "C" AS b,
 (CASE WHEN (g%200)%13=0 THEN NULL ELSE lpad((g%200)::text,1+(g%200)%63,'n') END)::name AS n,
 CASE WHEN (g%200)%9=0 THEN NULL ELSE g%200 END AS f,
 0 AS payload
FROM generate_series(1,20000)g;
CREATE INDEX corr_idx ON corr(a,b,n,f);
VACUUM (FREEZE,ANALYZE) corr;
CREATE OR REPLACE FUNCTION compare_paths(q text) RETURNS void LANGUAGE plpgsql AS $$
DECLARE expected text; actual text;
BEGIN
 PERFORM set_config('enable_seqscan','on',true);
 PERFORM set_config('enable_indexscan','off',true);
 PERFORM set_config('enable_indexonlyscan','off',true);
 PERFORM set_config('enable_bitmapscan','off',true);
 EXECUTE q INTO expected;
 PERFORM set_config('enable_seqscan','off',true);
 PERFORM set_config('enable_indexscan','on',true);
 PERFORM set_config('enable_indexonlyscan','on',true);
 EXECUTE q INTO actual;
 IF actual IS DISTINCT FROM expected THEN
  RAISE EXCEPTION 'result mismatch: expected %, actual %, SQL %', expected,actual,q;
 END IF;
END $$;
SELECT compare_paths($q$SELECT json_build_array(count(*),sum(hashtextextended(ROW(a,b,n,f)::text,0)::numeric))::text FROM corr$q$);
SELECT compare_paths($q$SELECT json_build_array(count(*),sum(hashtextextended(ROW(a,b,n,f)::text,0)::numeric))::text FROM corr WHERE b IS NULL$q$);
SELECT compare_paths($q$SELECT json_build_array(count(*),sum(hashtextextended(ROW(a,b,n,f)::text,0)::numeric))::text FROM corr WHERE f=ANY(ARRAY[1,2,10,70,151,199])$q$);
SELECT compare_paths($q$SELECT json_agg(x)::text FROM (SELECT a,b,n,f FROM corr ORDER BY a DESC,b DESC,n DESC,f DESC LIMIT 700) x$q$);
SELECT compare_paths($q$SELECT json_build_array(count(*),sum(hashtextextended(ROW(a,b,n,f)::text,0)::numeric))::text FROM corr WHERE a>='1' AND a<'3'$q$);
SET enable_seqscan=off;
SET enable_bitmapscan=off;
-- parameterized IOS rescans, including LIMIT and empty/missing keys
EXPLAIN (COSTS OFF) SELECT sum(q.n) FROM generate_series(0,299)g CROSS JOIN LATERAL (SELECT count(*) AS n FROM corr WHERE f=g)q;
SELECT sum(q.n) FROM generate_series(0,299)g CROSS JOIN LATERAL (SELECT count(*) AS n FROM corr WHERE f=g)q;
-- Scroll direction changes within a posting list and across workspace reuse
BEGIN;
DECLARE cur SCROLL CURSOR FOR SELECT a,b,n,f FROM corr ORDER BY a,b,n,f;
FETCH FORWARD 27 FROM cur;
FETCH BACKWARD 9 FROM cur;
MOVE FORWARD 1500 FROM cur;
FETCH BACKWARD 19 FROM cur;
MOVE BACKWARD 1450 FROM cur;
FETCH FORWARD 39 FROM cur;
CLOSE cur;
COMMIT;
-- Inner IOS under merge join exercises mark/restore.
CREATE TEMP TABLE join_left AS SELECT (g%200)::int AS f FROM generate_series(1,400)g;
CREATE INDEX ON join_left(f);
CREATE INDEX corr_f_idx ON corr(f,a,b,n);
VACUUM (FREEZE,ANALYZE) join_left;
VACUUM (FREEZE,ANALYZE) corr;
SET enable_hashjoin=off;
SET enable_nestloop=off;
SET enable_sort=off;
SET enable_material=off;
EXPLAIN (COSTS OFF) SELECT count(*) FROM join_left l JOIN corr c ON l.f=c.f;
SELECT count(*),sum(length(c.a)) FROM join_left l JOIN corr c ON l.f=c.f;
RESET enable_hashjoin;
RESET enable_nestloop;
RESET enable_sort;
RESET enable_material;
-- Volatile expressions must execute once per output row.
CREATE TEMP SEQUENCE volatile_probe;
SELECT count(*),max(nextval('volatile_probe')) FROM corr;
-- Invisible TIDs, including leading and wholly invisible runs; no vacuum.
DELETE FROM corr WHERE g%3=0 OR f<10;
UPDATE corr SET payload=payload+1 WHERE g%7=0;
UPDATE corr SET a=a||'x' WHERE g%11=0;
SELECT compare_paths($q$SELECT json_build_array(count(*),sum(hashtextextended(ROW(a,b,n,f)::text,0)::numeric))::text FROM corr$q$);
SELECT compare_paths($q$SELECT json_build_array(count(*),sum(hashtextextended(ROW(a,b,n,f)::text,0)::numeric))::text FROM corr WHERE b IS NULL$q$);
SELECT compare_paths($q$SELECT json_agg(x)::text FROM (SELECT a,b,n,f FROM corr ORDER BY a DESC,b DESC,n DESC,f DESC LIMIT 700) x$q$);
-- Parallel IOS has backend-private caches.
SET max_parallel_workers_per_gather=2;
SET min_parallel_index_scan_size=0;
SET parallel_setup_cost=0;
SET parallel_tuple_cost=0;
EXPLAIN (COSTS OFF) SELECT count(*) FROM wide;
SELECT count(*),sum(length(i)) FROM wide;
SELECT bt_index_check('corr_idx',true);
SELECT bt_index_check('corr_f_idx',true);
SELECT 'correctness passed';
-- One-attribute eligibility: int4, text and name (including NULLs).
CREATE TABLE one AS SELECT g,
 CASE WHEN g%200<4 THEN NULL ELSE g%200 END AS a,
 CASE WHEN g%200<4 THEN NULL ELSE repeat((g%200)::text,1+g%7) END COLLATE "C" AS t,
 (CASE WHEN g%200<4 THEN NULL ELSE lpad((g%200)::text,1+g%63,'n') END)::name AS n
 FROM generate_series(1,50000)g;
CREATE INDEX one_a ON one(a);
CREATE INDEX one_t ON one(t);
CREATE INDEX one_n ON one(n);
VACUUM (FREEZE,ANALYZE) one;
SELECT compare_paths($q$SELECT json_build_array(count(*),sum(a))::text FROM one$q$);
SELECT compare_paths($q$SELECT json_build_array(count(*),sum(hashtextextended(t,0)::numeric))::text FROM one$q$);
SELECT compare_paths($q$SELECT json_build_array(count(*),sum(hashtextextended(n::text,0)::numeric))::text FROM one$q$);
SELECT compare_paths($q$SELECT json_agg(x)::text FROM (SELECT n FROM one ORDER BY n DESC NULLS FIRST LIMIT 700)x$q$);
BEGIN;
DECLARE onecur SCROLL CURSOR FOR SELECT n FROM one ORDER BY n;
FETCH FORWARD 27 FROM onecur;
FETCH BACKWARD 9 FROM onecur;
MOVE FORWARD 3000 FROM onecur;
FETCH BACKWARD 19 FROM onecur;
MOVE BACKWARD 2900 FROM onecur;
FETCH FORWARD 39 FROM onecur;
CLOSE onecur;
COMMIT;
SELECT sum(q.n) FROM generate_series(0,299)g CROSS JOIN LATERAL (SELECT count(*)n FROM one WHERE a=g)q;
SET enable_hashjoin=off;SET enable_nestloop=off;SET enable_sort=off;SET enable_material=off;
EXPLAIN (COSTS OFF) SELECT count(*) FROM join_left l JOIN one o ON l.f=o.a;
SELECT count(*),sum(o.a) FROM join_left l JOIN one o ON l.f=o.a;
RESET enable_hashjoin;RESET enable_nestloop;RESET enable_sort;RESET enable_material;
DELETE FROM one WHERE g%3=0;
SELECT compare_paths($q$SELECT json_build_array(count(*),sum(a))::text FROM one$q$);
SELECT compare_paths($q$SELECT json_agg(x)::text FROM (SELECT n FROM one ORDER BY n DESC NULLS FIRST LIMIT 700)x$q$);
SELECT bt_index_check('one_a',true),bt_index_check('one_t',true),bt_index_check('one_n',true);
DROP TABLE one;
-- Full 32-attribute nullable/mixed byval/TEXT/name projection checks.
CREATE TABLE many AS SELECT g,CASE WHEN k%3=0 THEN NULL ELSE (k+1)::int END AS m1,CASE WHEN k%4=0 THEN NULL ELSE repeat((k+2)::text,1+k%7)COLLATE "C" END AS m2,CASE WHEN k%5=0 THEN NULL ELSE lpad((k+3)::text,1+(k+3)%63,'n')::name END AS m3,CASE WHEN k%6=0 THEN NULL ELSE (k+4)::bigint END AS m4,CASE WHEN k%7=0 THEN NULL ELSE (k+5)::int END AS m5,CASE WHEN k%8=0 THEN NULL ELSE repeat((k+6)::text,1+k%7)COLLATE "C" END AS m6,CASE WHEN k%9=0 THEN NULL ELSE lpad((k+7)::text,1+(k+7)%63,'n')::name END AS m7,CASE WHEN k%10=0 THEN NULL ELSE (k+8)::bigint END AS m8,CASE WHEN k%11=0 THEN NULL ELSE (k+9)::int END AS m9,CASE WHEN k%12=0 THEN NULL ELSE repeat((k+10)::text,1+k%7)COLLATE "C" END AS m10,CASE WHEN k%13=0 THEN NULL ELSE lpad((k+11)::text,1+(k+11)%63,'n')::name END AS m11,CASE WHEN k%14=0 THEN NULL ELSE (k+12)::bigint END AS m12,CASE WHEN k%15=0 THEN NULL ELSE (k+13)::int END AS m13,CASE WHEN k%16=0 THEN NULL ELSE repeat((k+14)::text,1+k%7)COLLATE "C" END AS m14,CASE WHEN k%17=0 THEN NULL ELSE lpad((k+15)::text,1+(k+15)%63,'n')::name END AS m15,CASE WHEN k%18=0 THEN NULL ELSE (k+16)::bigint END AS m16,CASE WHEN k%19=0 THEN NULL ELSE (k+17)::int END AS m17,CASE WHEN k%20=0 THEN NULL ELSE repeat((k+18)::text,1+k%7)COLLATE "C" END AS m18,CASE WHEN k%21=0 THEN NULL ELSE lpad((k+19)::text,1+(k+19)%63,'n')::name END AS m19,CASE WHEN k%22=0 THEN NULL ELSE (k+20)::bigint END AS m20,CASE WHEN k%23=0 THEN NULL ELSE (k+21)::int END AS m21,CASE WHEN k%24=0 THEN NULL ELSE repeat((k+22)::text,1+k%7)COLLATE "C" END AS m22,CASE WHEN k%25=0 THEN NULL ELSE lpad((k+23)::text,1+(k+23)%63,'n')::name END AS m23,CASE WHEN k%26=0 THEN NULL ELSE (k+24)::bigint END AS m24,CASE WHEN k%27=0 THEN NULL ELSE (k+25)::int END AS m25,CASE WHEN k%28=0 THEN NULL ELSE repeat((k+26)::text,1+k%7)COLLATE "C" END AS m26,CASE WHEN k%29=0 THEN NULL ELSE lpad((k+27)::text,1+(k+27)%63,'n')::name END AS m27,CASE WHEN k%30=0 THEN NULL ELSE (k+28)::bigint END AS m28,CASE WHEN k%31=0 THEN NULL ELSE (k+29)::int END AS m29,CASE WHEN k%32=0 THEN NULL ELSE repeat((k+30)::text,1+k%7)COLLATE "C" END AS m30,CASE WHEN k%33=0 THEN NULL ELSE lpad((k+31)::text,1+(k+31)%63,'n')::name END AS m31,CASE WHEN k%34=0 THEN NULL ELSE (k+32)::bigint END AS m32 FROM (SELECT g,g%127 k FROM generate_series(1,20000)g)s;
CREATE INDEX many_idx ON many(m1,m2,m3,m4,m5,m6,m7,m8,m9,m10,m11,m12,m13,m14,m15,m16,m17,m18,m19,m20,m21,m22,m23,m24,m25,m26,m27,m28,m29,m30,m31,m32);
VACUUM (FREEZE,ANALYZE) many;
EXPLAIN (COSTS OFF) SELECT sum(hashtextextended(ROW(m1,m2,m3,m4,m5,m6,m7,m8,m9,m10,m11,m12,m13,m14,m15,m16,m17,m18,m19,m20,m21,m22,m23,m24,m25,m26,m27,m28,m29,m30,m31,m32)::text,0)::numeric) FROM many;
SELECT compare_paths($q$SELECT json_build_array(count(*),sum(hashtextextended(ROW(m1,m2,m3,m4,m5,m6,m7,m8,m9,m10,m11,m12,m13,m14,m15,m16,m17,m18,m19,m20,m21,m22,m23,m24,m25,m26,m27,m28,m29,m30,m31,m32)::text,0)::numeric))::text FROM many$q$);
DELETE FROM many WHERE g%5=0;
SELECT compare_paths($q$SELECT json_build_array(count(*),sum(hashtextextended(ROW(m1,m2,m3,m4,m5,m6,m7,m8,m9,m10,m11,m12,m13,m14,m15,m16,m17,m18,m19,m20,m21,m22,m23,m24,m25,m26,m27,m28,m29,m30,m31,m32)::text,0)::numeric))::text FROM many$q$);
SELECT bt_index_check('many_idx',true);
DROP TABLE many;
CREATE TABLE short2 AS SELECT g,CASE WHEN k%3=0 THEN NULL ELSE (k+0)::int END AS m1,CASE WHEN k%4=0 THEN NULL ELSE repeat(k::text,2) COLLATE "C" END AS m2 FROM(SELECT g,g%97 k FROM generate_series(1,20000)g)s;
CREATE INDEX short2_idx ON short2(m1,m2);
VACUUM(FREEZE,ANALYZE)short2;
SELECT compare_paths($q$SELECT json_build_array(count(*),sum(hashtextextended(ROW(m1,m2)::text,0)::numeric))::text FROM short2$q$);
DELETE FROM short2 WHERE g%3=0;
SELECT compare_paths($q$SELECT json_build_array(count(*),sum(hashtextextended(ROW(m1,m2)::text,0)::numeric))::text FROM short2$q$);
SELECT bt_index_check('short2_idx',true);
DROP TABLE short2;
CREATE TABLE short3 AS SELECT g,CASE WHEN k%3=0 THEN NULL ELSE (k+0)::int END AS m1,CASE WHEN k%4=0 THEN NULL ELSE repeat(k::text,2) COLLATE "C" END AS m2,CASE WHEN k%5=0 THEN NULL ELSE repeat(k::text,3) COLLATE "C" END AS m3 FROM(SELECT g,g%97 k FROM generate_series(1,20000)g)s;
CREATE INDEX short3_idx ON short3(m1,m2,m3);
VACUUM(FREEZE,ANALYZE)short3;
SELECT compare_paths($q$SELECT json_build_array(count(*),sum(hashtextextended(ROW(m1,m2,m3)::text,0)::numeric))::text FROM short3$q$);
DELETE FROM short3 WHERE g%3=0;
SELECT compare_paths($q$SELECT json_build_array(count(*),sum(hashtextextended(ROW(m1,m2,m3)::text,0)::numeric))::text FROM short3$q$);
SELECT bt_index_check('short3_idx',true);
DROP TABLE short3;
DROP FUNCTION compare_paths(text);
DROP TABLE corr;
