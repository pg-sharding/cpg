-- prepare_update_heavy.sql — create table for UPDATE-heavy benchmark
-- Run once on primary before starting update-heavy scenario
DROP TABLE IF EXISTS updtest;
CREATE TABLE updtest(id integer PRIMARY KEY, val integer, data text);
INSERT INTO updtest
SELECT i, 0, repeat('x', 100) FROM generate_series(1, 100000) i;
