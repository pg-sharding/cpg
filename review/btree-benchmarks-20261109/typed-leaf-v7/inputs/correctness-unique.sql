\set ON_ERROR_STOP on
\pset tuples_only on
\pset format unaligned
CREATE TABLE sep_unique(k bigint);
INSERT INTO sep_unique SELECT g FROM generate_series(1,50000) g;
CREATE UNIQUE INDEX sep_unique_idx ON sep_unique(k);
SET enable_seqscan=off;
SET enable_bitmapscan=off;
SET jit=off;
SELECT sum((SELECT k FROM sep_unique WHERE k=((g*7919::bigint)%50000)+1)) FROM generate_series(1,10000)g;
-- Unique-checking insertion omits scantid during its initial descent.
INSERT INTO sep_unique SELECT g FROM generate_series(50001,150000)g;
INSERT INTO sep_unique SELECT g FROM generate_series(1,1000)g ON CONFLICT DO NOTHING;
DO $$ BEGIN
 BEGIN
  INSERT INTO sep_unique VALUES(42);
  RAISE EXCEPTION 'unique constraint was bypassed';
 EXCEPTION WHEN unique_violation THEN NULL;
 END;
END $$;
SELECT count(*),sum(k) FROM sep_unique;
SELECT bt_index_parent_check('sep_unique_idx',true,true);
SELECT 'unique-checking-insert:ok';
