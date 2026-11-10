-- MODULE is a psql variable bound to the freshly compiled diagnostic .so.
CREATE SCHEMA cache_probe;
CREATE FUNCTION cache_probe.bool_support(internal,smallint,tsvector,integer,internal,internal,internal,internal)
RETURNS boolean AS :'MODULE','gin_vector_probe_bool' LANGUAGE C STRICT VOLATILE;
CREATE FUNCTION cache_probe.tri_support(internal,smallint,tsvector,integer,internal,internal,internal)
RETURNS "char" AS :'MODULE','gin_vector_probe_tri' LANGUAGE C STRICT VOLATILE;
CREATE FUNCTION cache_probe.reset() RETURNS void AS :'MODULE','gin_vector_probe_reset' LANGUAGE C VOLATILE;
CREATE FUNCTION cache_probe.report() RETURNS text AS :'MODULE','gin_vector_probe_report' LANGUAGE C VOLATILE;
CREATE OPERATOR CLASS cache_probe.probe_ops FOR TYPE tsvector USING gin AS
 OPERATOR 1 @@ (tsvector,tsquery),
 FUNCTION 1 pg_catalog.gin_cmp_tslexeme(text,text),
 FUNCTION 2 pg_catalog.gin_extract_tsvector(tsvector,internal,internal),
 FUNCTION 3 pg_catalog.gin_extract_tsquery(tsvector,internal,smallint,internal,internal,internal,internal),
 FUNCTION 4 cache_probe.bool_support(internal,smallint,tsvector,integer,internal,internal,internal,internal),
 FUNCTION 5 pg_catalog.gin_cmp_prefix(text,text,smallint,internal),
 FUNCTION 6 cache_probe.tri_support(internal,smallint,tsvector,integer,internal,internal,internal),
 STORAGE text;
CREATE TABLE cache_probe.docs AS SELECT id,d FROM g1.docs;
CREATE INDEX probe_d_gin ON cache_probe.docs USING gin(d cache_probe.probe_ops) WITH(fastupdate=off);
VACUUM(FREEZE,ANALYZE) cache_probe.docs;
