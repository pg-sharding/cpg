\set ON_ERROR_STOP on
CREATE EXTENSION intarray;
CREATE SCHEMA g1;
SET search_path=g1,public,pg_catalog;
SET jit=off;
CREATE TABLE docs(id bigint PRIMARY KEY,d tsvector,tags integer[],jb jsonb);
INSERT INTO docs
SELECT g,to_tsvector('simple', 'common '||CASE WHEN g%2=0 THEN 'dense2 ' ELSE '' END||CASE WHEN g%3=0 THEN 'dense3 ' ELSE '' END||CASE WHEN g%1000=0 THEN 'rare0 ' ELSE '' END||CASE WHEN g%1013=0 THEN 'rare1 ' ELSE '' END||CASE WHEN g%127=0 THEN 'rare2 ' ELSE '' END||CASE WHEN g%17=0 THEN 'rare3 ' ELSE '' END||'group'||(g%4096)::text),
ARRAY[1,CASE WHEN g%2=0 THEN 2 ELSE 3 END,CASE WHEN g%1000=0 THEN 1001 ELSE 4 END,CASE WHEN g%1013=0 THEN 1002 ELSE 5 END,(g%97)::int+10000],
jsonb_build_object('common',true)||CASE WHEN g%1000=0 THEN '{"rare":42}'::jsonb ELSE '{"other":17}'::jsonb END
FROM generate_series(1,200000)g;
INSERT INTO docs VALUES(-1,NULL,NULL,NULL),(-2,''::tsvector,ARRAY[]::int[],'{}');
CREATE INDEX docs_d_gin ON docs USING gin(d) WITH(fastupdate=off);
CREATE INDEX docs_tags_gin ON docs USING gin(tags gin__int_ops) WITH(fastupdate=off);
CREATE INDEX docs_jb_gin ON docs USING gin(jb) WITH(fastupdate=off);
CREATE TABLE builtin_arrays AS SELECT id,tags FROM docs;
CREATE INDEX builtin_tags_gin ON builtin_arrays USING gin(tags pg_catalog.array_ops) WITH(fastupdate=off);
CREATE TABLE inline_docs AS SELECT g id,to_tsvector('simple','common token'||(g%64)::text) d FROM generate_series(1,256)g;
CREATE INDEX inline_d_gin ON inline_docs USING gin(d) WITH(fastupdate=off);
CREATE TABLE writes AS TABLE docs WITH NO DATA;
INSERT INTO writes SELECT * FROM docs WHERE id BETWEEN 1 AND 5000;
CREATE INDEX writes_d_gin ON writes USING gin(d) WITH(fastupdate=on);
VACUUM(FREEZE,ANALYZE) docs;
VACUUM(FREEZE,ANALYZE) builtin_arrays;
VACUUM(FREEZE,ANALYZE) inline_docs;
VACUUM(FREEZE,ANALYZE) writes;
CHECKPOINT;
