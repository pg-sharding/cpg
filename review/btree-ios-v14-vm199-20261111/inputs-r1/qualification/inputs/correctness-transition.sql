\set ON_ERROR_STOP on
SET client_min_messages=warning;
SET jit=off;
SET max_parallel_workers_per_gather=0;
SET enable_memoize=off;
CREATE EXTENSION IF NOT EXISTS pageinspect;
CREATE TEMP TABLE transition_mix(a int,b text,n name);
INSERT INTO transition_mix
SELECT g,lpad(g::text,12,'x'),CASE WHEN g%11=0 THEN NULL ELSE lpad(g::text,1+g%63,'n')::name END
FROM generate_series(1,12000)g;
INSERT INTO transition_mix
SELECT g,lpad(g::text,12,'x'),CASE WHEN g%11=0 THEN NULL ELSE lpad(g::text,1+g%63,'n')::name END
FROM generate_series(1,12000)g CROSS JOIN generate_series(1,63)d WHERE g%128=0;
CREATE INDEX transition_mix_idx ON transition_mix(a,b,n);
VACUUM(FREEZE,ANALYZE)transition_mix;
SELECT count(*)>0 AS real_posting_tuples FROM generate_series(1,10)p
CROSS JOIN LATERAL bt_page_items('transition_mix_idx',p) WHERE tids IS NOT NULL;

-- Compare all indexed values against independent sequential scans.
DO $$
DECLARE expected text;actual text;
BEGIN
 PERFORM set_config('enable_indexscan','off',true);
 PERFORM set_config('enable_indexonlyscan','off',true);
 PERFORM set_config('enable_bitmapscan','off',true);
 SELECT json_build_array(count(*),sum(hashtextextended(ROW(a,b,n)::text,0)::numeric))::text INTO expected FROM transition_mix;
 PERFORM set_config('enable_indexscan','on',true);
 PERFORM set_config('enable_indexonlyscan','on',true);
 PERFORM set_config('enable_seqscan','off',true);
 SELECT json_build_array(count(*),sum(hashtextextended(ROW(a,b,n)::text,0)::numeric))::text INTO actual FROM transition_mix;
 IF actual<>expected THEN RAISE EXCEPTION 'mixed IOS mismatch';END IF;
END$$;
SET enable_seqscan=off;
SET enable_bitmapscan=off;
SET enable_indexonlyscan=on;
SET enable_indexscan=on;
EXPLAIN(COSTS OFF)SELECT a,b,n FROM transition_mix ORDER BY a,b,n;
BEGIN;
DECLARE tr SCROLL CURSOR FOR SELECT a,b,n FROM transition_mix ORDER BY a,b,n;
MOVE FORWARD 127 IN tr;
FETCH FORWARD 5 FROM tr;
FETCH BACKWARD 5 FROM tr;
MOVE FORWARD 300 IN tr;
FETCH BACKWARD 5 FROM tr;
MOVE FORWARD ALL IN tr;
FETCH BACKWARD 5 FROM tr;
MOVE BACKWARD ALL IN tr;
FETCH FORWARD 5 FROM tr;
CLOSE tr;
COMMIT;

-- Rescan many times at posting/singleton boundaries, with name conversion.
SELECT sum(q.h) FROM generate_series(120,150)g CROSS JOIN LATERAL
(SELECT sum(hashtextextended(ROW(b,n)::text,0)::numeric)h FROM
 (SELECT b,n FROM transition_mix WHERE a=g ORDER BY b,n LIMIT 2)s)q;

-- Force a merge join that can mark/restore its inner ordered scan.
CREATE TEMP TABLE transition_probe AS SELECT (g%128)*128 AS a FROM generate_series(1,1200)g;
CREATE INDEX transition_probe_idx ON transition_probe(a);
VACUUM(FREEZE,ANALYZE)transition_probe;
SET enable_hashjoin=off;
SET enable_nestloop=off;
SET enable_material=off;
EXPLAIN(COSTS OFF)SELECT count(*)FROM transition_probe p JOIN transition_mix t USING(a);
SELECT count(*)FROM transition_probe p JOIN transition_mix t USING(a);
RESET enable_hashjoin;RESET enable_nestloop;RESET enable_material;

-- Invisible/deleted TIDs must not leave a stale deformation attachment.
DELETE FROM transition_mix WHERE ctid IN(SELECT ctid FROM transition_mix WHERE a%128=0 AND (ctid::text::point)[1]::int%2=0);
DO $$
DECLARE expected text;actual text;
BEGIN
 PERFORM set_config('enable_indexscan','off',true);
 PERFORM set_config('enable_indexonlyscan','off',true);
 PERFORM set_config('enable_seqscan','on',true);
 SELECT json_build_array(count(*),sum(hashtextextended(ROW(a,b,n)::text,0)::numeric))::text INTO expected FROM transition_mix;
 PERFORM set_config('enable_indexscan','on',true);
 PERFORM set_config('enable_indexonlyscan','on',true);
 PERFORM set_config('enable_seqscan','off',true);
 SELECT json_build_array(count(*),sum(hashtextextended(ROW(a,b,n)::text,0)::numeric))::text INTO actual FROM transition_mix;
 IF actual<>expected THEN RAISE EXCEPTION 'mixed invisible IOS mismatch';END IF;
END$$;
SELECT bt_index_check('transition_mix_idx',true);
SELECT 'transition lifecycle PASS';
