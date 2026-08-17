-- prepare_tables.sql — create tables needed by custom pgbench scripts
-- Run once on primary before starting scenarios that use custom scripts

-- For smalltx.sql (S3)
CREATE TABLE IF NOT EXISTS smalltx(id integer, payload text);

-- For copy_bulk.sql (S4)
CREATE TABLE IF NOT EXISTS big(id integer, data text);

-- For walheavy.sql (alternative S3)
CREATE TABLE IF NOT EXISTS accounts(aid integer PRIMARY KEY, abalance integer);
CREATE TABLE IF NOT EXISTS audit(aid integer, ts timestamptz);

-- Seed accounts for walheavy
INSERT INTO accounts SELECT i, 0 FROM generate_series(1, 1000) i
ON CONFLICT DO NOTHING;
