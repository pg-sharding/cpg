\set ON_ERROR_STOP on
SET client_min_messages=warning;
CREATE SCHEMA s2;
SET search_path=s2,pg_catalog;
CREATE TABLE boxes(id int NOT NULL, b box, payload int);
INSERT INTO boxes SELECT g,
 CASE WHEN g%1009=0 THEN NULL ELSE box(point((g%1000)::float8,(g/1000)::float8),point((g%1000)::float8+0.7,(g/1000)::float8+0.7)) END,
 (g*17)%10000 FROM generate_series(1,200000)g;
CREATE INDEX boxes_gist ON boxes USING gist(b);
CREATE TABLE probes(id int,q box);
INSERT INTO probes SELECT g,box(point(((g::bigint*7919)%1000)::float8,((g::bigint*104729)%200)::float8),point(((g::bigint*7919)%1000)::float8+0.01,((g::bigint*104729)%200)::float8+0.01)) FROM generate_series(1,512)g;
CREATE TABLE tiny AS SELECT * FROM boxes WHERE id<=16;
CREATE INDEX tiny_gist ON tiny USING gist(b);
CREATE TABLE saturated(id int,b box);
INSERT INTO saturated SELECT g,box(point(-100,-100),point(100,100)) FROM generate_series(1,60000)g;
CREATE INDEX saturated_gist ON saturated USING gist(b);
CREATE TABLE points(id int,p point);
INSERT INTO points SELECT id,center(b) FROM boxes WHERE b IS NOT NULL;
CREATE INDEX points_gist ON points USING gist(p);
CREATE TABLE wrapped AS SELECT * FROM boxes WHERE id<=32000;
CREATE FUNCTION forward_consistent(internal,box,int2,oid,internal) RETURNS bool AS :'module','gist_batch_forward_consistent' LANGUAGE C IMMUTABLE STRICT;
CREATE OPERATOR CLASS s2_box_ops FOR TYPE box USING gist AS
 OPERATOR 3 &&(box,box),
 FUNCTION 1 s2.forward_consistent(internal,box,int2,oid,internal),
 FUNCTION 2 gist_box_union(internal,internal),
 FUNCTION 5 gist_box_penalty(internal,internal,internal),
 FUNCTION 6 gist_box_picksplit(internal,internal),
 FUNCTION 7 gist_box_same(box,box,internal);
CREATE INDEX wrapped_gist ON wrapped USING gist(b s2_box_ops);
CREATE TABLE edges(id int,b box);
INSERT INTO edges VALUES
 (1,'((0,0),(0,0))'),(2,'((0.000001,0),(0.000001,0))'),
 (3,'((0.0000010000000000000002,0),(0.0000010000000000000002,0))'),
 (4,'((0.0000009999999999999998,0),(0.0000009999999999999998,0))'),
 (5,'((Infinity,Infinity),(-Infinity,-Infinity))'),
 (6,'((Infinity,Infinity),(Infinity,Infinity))'),
 (7,'((-Infinity,-Infinity),(-Infinity,-Infinity))'),
 (8,'((NaN,0),(NaN,0))'),(9,'((0,NaN),(0,NaN))'),(10,NULL),
 (11,'((-0,-0),(0,0))');
CREATE INDEX edges_gist ON edges USING gist(b);
VACUUM (FREEZE,ANALYZE) boxes;
VACUUM (FREEZE,ANALYZE) probes;
VACUUM (FREEZE,ANALYZE) tiny;
VACUUM (FREEZE,ANALYZE) saturated;
VACUUM (FREEZE,ANALYZE) points;
VACUUM (FREEZE,ANALYZE) wrapped;
VACUUM (FREEZE,ANALYZE) edges;
CHECKPOINT;
