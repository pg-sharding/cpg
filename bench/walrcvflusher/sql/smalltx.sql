-- smalltx.sql — S3: high WAL rate, small transactions
-- Each transaction generates minimal WAL: one INSERT
-- Usage: pgbench -f sql/smalltx.sql --client=64 --no-vacuum --transactions=100000

\set n random(1, 100000000)
INSERT INTO smalltx(id, payload) VALUES (:n, repeat('x', 50));
