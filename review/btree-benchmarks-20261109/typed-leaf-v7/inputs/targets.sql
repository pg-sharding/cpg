\set ON_ERROR_STOP on
\pset format unaligned
\pset tuples_only on
SET jit=off;
SET max_parallel_workers_per_gather=0;
CREATE EXTENSION IF NOT EXISTS amcheck;
CREATE EXTENSION IF NOT EXISTS pageinspect;
CREATE TABLE typed_perm(k bigint,v bigint);
INSERT INTO typed_perm SELECT g,g::bigint*3 FROM generate_series(-30000,30000)g;
INSERT INTO typed_perm SELECT 3,g FROM generate_series(1,60000)g;
INSERT INTO typed_perm VALUES('-9223372036854775808',1),('9223372036854775807',2),(NULL,3);
CREATE INDEX typed_perm_idx ON typed_perm(k);
CREATE UNLOGGED TABLE typed_unlogged AS TABLE typed_perm;
CREATE INDEX typed_unlogged_idx ON typed_unlogged(k);
CREATE TEMP TABLE typed_temp AS TABLE typed_perm;
CREATE INDEX typed_temp_idx ON typed_temp(k);
VACUUM (ANALYZE) typed_perm;
VACUUM (ANALYZE) typed_unlogged;
VACUUM (ANALYZE) typed_temp;
CREATE FUNCTION typed_ref(label text,q text) RETURNS text LANGUAGE plpgsql AS $$
DECLARE a text;b text;
BEGIN
 PERFORM set_config('enable_seqscan','on',true);
 PERFORM set_config('enable_indexscan','off',true);
 PERFORM set_config('enable_indexonlyscan','off',true);
 PERFORM set_config('enable_bitmapscan','off',true);
 EXECUTE q INTO a;
 PERFORM set_config('enable_seqscan','off',true);
 PERFORM set_config('enable_indexscan','on',true);
 PERFORM set_config('enable_indexonlyscan','on',true);
 EXECUTE q INTO b;
 IF a IS DISTINCT FROM b THEN RAISE EXCEPTION '% expected %, got %',label,a,b;END IF;
 RETURN label||':ok:'||coalesce(a,'NULL');
END$$;
CREATE FUNCTION typed_sweep(t regclass,label text) RETURNS text LANGUAGE plpgsql AS $$
DECLARE k bigint; op text;n int:=0;
BEGIN
 FOR k IN SELECT v FROM (VALUES('-9223372036854775808'::bigint),(-30001),(-30000),(-1),(0),(2),(3),(4),(29999),(30000),(30001),('9223372036854775807'::bigint))x(v) LOOP
  FOREACH op IN ARRAY ARRAY['=','<','<=','>','>='] LOOP
   PERFORM typed_ref(label||op||k,format('SELECT concat(count(*),'':'',sum(v)) FROM %s WHERE k %s %L::bigint',t,op,k));n:=n+1;
   PERFORM typed_ref(label||':limit:'||op||k,format('SELECT md5(string_agg(k::text,'','' ORDER BY k DESC)) FROM (SELECT k FROM %s WHERE k %s %L::bigint ORDER BY k DESC LIMIT 21)q',t,op,k));n:=n+1;
  END LOOP;
 END LOOP;
 PERFORM typed_ref(label||':null',format('SELECT count(*)::text FROM %s WHERE k IS NULL',t));
 PERFORM typed_ref(label||':cross',format('SELECT count(*)::text FROM %s WHERE k=3::int4',t));
 PERFORM typed_ref(label||':saop',format('SELECT concat(count(*),'':'',sum(v)) FROM %s WHERE k=ANY(ARRAY[-30000,3,4,NULL,30000]::bigint[])',t));
 RETURN label||':ok:'||n;
END$$;
SELECT typed_sweep('typed_perm','permanent');
SELECT typed_sweep('typed_unlogged','unlogged');
SELECT typed_sweep('typed_temp','temp');
PREPARE typed_param(bigint) AS SELECT count(*),sum(v) FROM typed_perm WHERE k=$1;
EXECUTE typed_param(3);EXECUTE typed_param(NULL);EXECUTE typed_param('-9223372036854775808');EXECUTE typed_param(30000);
DEALLOCATE typed_param;
SELECT typed_ref('rescan','SELECT sum((SELECT count(*) FROM typed_perm WHERE k=g))::text FROM unnest(ARRAY[-30000,3,4,NULL,30000]::bigint[])g');
BEGIN;
SET LOCAL enable_seqscan=off;
DECLARE typed_cursor SCROLL CURSOR FOR SELECT k FROM typed_perm WHERE k>=-10::bigint AND k<=10::bigint ORDER BY k;
FETCH FORWARD 5 FROM typed_cursor;
MOVE FORWARD 10 FROM typed_cursor;
FETCH BACKWARD 4 FROM typed_cursor;
MOVE ABSOLUTE 1 FROM typed_cursor;
FETCH FORWARD 3 FROM typed_cursor;
ROLLBACK;
CREATE TABLE typed_desc AS TABLE typed_perm;CREATE INDEX typed_desc_idx ON typed_desc(k DESC NULLS FIRST);
SELECT typed_sweep('typed_desc','desc-fallback');
CREATE TABLE typed_include AS TABLE typed_perm;CREATE INDEX typed_include_idx ON typed_include(k) INCLUDE(v);
SELECT typed_sweep('typed_include','include-fallback');
CREATE TABLE typed_multi AS TABLE typed_perm;CREATE INDEX typed_multi_idx ON typed_multi(k,v);
SELECT typed_sweep('typed_multi','multikey-fallback');
CREATE FUNCTION typed_custom_cmp(bigint,bigint) RETURNS int LANGUAGE SQL IMMUTABLE STRICT PARALLEL SAFE AS 'SELECT CASE WHEN $1<$2 THEN -1 WHEN $1>$2 THEN 1 ELSE 0 END';
CREATE OPERATOR CLASS typed_custom_ops FOR TYPE bigint USING btree AS OPERATOR 1 < (bigint,bigint),OPERATOR 2 <= (bigint,bigint),OPERATOR 3 = (bigint,bigint),OPERATOR 4 >= (bigint,bigint),OPERATOR 5 > (bigint,bigint),FUNCTION 1 typed_custom_cmp(bigint,bigint);
CREATE TABLE typed_custom AS TABLE typed_perm;CREATE INDEX typed_custom_idx ON typed_custom(k typed_custom_ops);
SELECT typed_sweep('typed_custom','new-oid-opclass-fallback');
CREATE TABLE typed_null_first AS TABLE typed_perm;CREATE INDEX typed_null_first_idx ON typed_null_first(k NULLS FIRST);
SELECT typed_sweep('typed_null_first','nulls-first');
SELECT bt_index_parent_check('typed_perm_idx',true,true);
SELECT bt_index_parent_check('typed_unlogged_idx',true,true);
SELECT bt_index_parent_check('typed_temp_idx',true,true);
CREATE TABLE typed_empty(k bigint);CREATE INDEX typed_empty_idx ON typed_empty(k);
SET enable_seqscan=off;
SELECT count(*) FROM typed_empty WHERE k>=0::bigint;
INSERT INTO typed_empty VALUES(1),(2);DELETE FROM typed_empty;VACUUM typed_empty;
SELECT count(*) FROM typed_empty WHERE k<=0::bigint;
SELECT 'typed-targets:ok';
