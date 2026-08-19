-- copy_highwal.sql — S4b: maximum WAL throughput via large INSERT
-- Generates ~100MB WAL per "transaction" via INSERT ... SELECT generate_series
-- Usage: pgbench -f sql/copy_highwal.sql --client=4 --no-vacuum --transactions=10
--
-- Each "transaction" inserts 500k rows with 100-byte payload → ~50MB WAL
-- With 4 clients × 10 transactions = 40 transactions → ~2GB WAL total

\set n 500000
INSERT INTO big SELECT g, md5(g::text)||repeat('x', 60) FROM generate_series(1, :n) g;
