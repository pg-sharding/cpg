CREATE EXTENSION amcheck;
CREATE TABLE wide AS
SELECT g, repeat((g%10000)::text,8) COLLATE "C" AS i,
       repeat((g%10000)::text,9) COLLATE "C" AS j
FROM generate_series(1,200000) g;
CREATE INDEX wide_idx ON wide(i,j);
VACUUM (FREEZE,ANALYZE) wide;
CHECKPOINT;
SELECT count(*),sum(length(i)) FROM wide;
