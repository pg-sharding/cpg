-- copy_bulk.sql — S4: large transactions, continuous WAL stream
-- One "transaction" inserts a large batch, generating a long WAL stream
-- Usage: pgbench -f sql/copy_bulk.sql --client=1 --no-vacuum --transactions=1

\set n 100000
INSERT INTO big SELECT generate_series(1, :n), md5(g::text) FROM generate_series(1, :n) g;
