-- walheavy.sql — high-WAL scenario with full-page images
-- Each transaction: UPDATE 10 random rows + INSERT 100 rows into audit
-- Generates FPI when pages are first dirtied after checkpoint
-- Usage: pgbench -f sql/walheavy.sql --client=32 --no-vacuum --time=30

\set n random(1, 1000)
\set m random(1, 1000)
\set k random(1, 1000)
BEGIN;
UPDATE accounts SET abalance = abalance + 1 WHERE aid IN (:n, :m, :k, :n+1, :m+1);
INSERT INTO audit SELECT g, clock_timestamp() FROM generate_series(1, 100) g;
COMMIT;
