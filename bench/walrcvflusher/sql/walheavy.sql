-- walheavy.sql — alternative high-WAL scenario
-- Each transaction: UPDATE + INSERT (generates full-page images on first dirty)
-- Usage: pgbench -f sql/walheavy.sql --client=32 --no-vacuum

\set n random(1, 1000)
BEGIN;
UPDATE accounts SET abalance = abalance + 1 WHERE aid = :n;
INSERT INTO audit VALUES (:n, clock_timestamp());
COMMIT;
