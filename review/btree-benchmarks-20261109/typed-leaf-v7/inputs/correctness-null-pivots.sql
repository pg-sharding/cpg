\set ON_ERROR_STOP on
DROP TABLE IF EXISTS sep_null_pivots;
CREATE TABLE sep_null_pivots(k bigint);
INSERT INTO sep_null_pivots SELECT CASE WHEN g%2=0 THEN NULL ELSE g::bigint END FROM generate_series(1,400000)g;
CREATE INDEX sep_null_pivots_idx ON sep_null_pivots(k) WITH (deduplicate_items=off);
VACUUM (ANALYZE) sep_null_pivots;
SET enable_seqscan=off;
SET enable_bitmapscan=off;
SET jit=off;
DO $$DECLARE i int; x bigint; n bigint; BEGIN
 FOR i IN 1..2000 LOOP
  x:=(i*7919::bigint)%400000;
  SELECT count(*) INTO n FROM sep_null_pivots WHERE k=x;
  IF n<>(CASE WHEN x%2=1 THEN 1 ELSE 0 END) THEN RAISE EXCEPTION 'NULL LAST mismatch % %',x,n; END IF;
 END LOOP;
END$$;
SELECT bt_index_parent_check('sep_null_pivots_idx',true,true);
DROP INDEX sep_null_pivots_idx;
CREATE INDEX sep_null_pivots_idx ON sep_null_pivots(k ASC NULLS FIRST) WITH (deduplicate_items=off);
VACUUM (ANALYZE) sep_null_pivots;
DO $$DECLARE i int; x bigint; n bigint; BEGIN
 FOR i IN 1..2000 LOOP
  x:=(i*7919::bigint)%400000;
  SELECT count(*) INTO n FROM sep_null_pivots WHERE k=x;
  IF n<>(CASE WHEN x%2=1 THEN 1 ELSE 0 END) THEN RAISE EXCEPTION 'NULL FIRST mismatch % %',x,n; END IF;
 END LOOP;
END$$;
SELECT bt_index_parent_check('sep_null_pivots_idx',true,true);
SELECT 'NULL tagged pivots:ok';
