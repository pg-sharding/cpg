-- update_heavy.sql — high-WAL scenario, UPDATE-only (no table growth)
-- Each transaction: UPDATE 20 random rows with ~640 bytes payload
-- With checkpoint_timeout=30s, FPI generated frequently
-- Usage: pgbench -f update_heavy.sql -c 32 -j 8 -T 60

\set n1 random(1, 100000)
\set n2 random(1, 100000)
\set n3 random(1, 100000)
\set n4 random(1, 100000)
\set n5 random(1, 100000)
\set n6 random(1, 100000)
\set n7 random(1, 100000)
\set n8 random(1, 100000)
\set n9 random(1, 100000)
\set n10 random(1, 100000)
\set n11 random(1, 100000)
\set n12 random(1, 100000)
\set n13 random(1, 100000)
\set n14 random(1, 100000)
\set n15 random(1, 100000)
\set n16 random(1, 100000)
\set n17 random(1, 100000)
\set n18 random(1, 100000)
\set n19 random(1, 100000)
\set n20 random(1, 100000)
\set seed random(1, 999999999)
BEGIN;
UPDATE updtest SET val = :seed, data = md5(:seed::text) || md5(:n1::text) || md5(:n2::text) || md5(:n3::text) || md5(:n4::text) || md5(:n5::text) || md5(:n6::text) || md5(:n7::text) || md5(:n8::text) || md5(:n9::text) || md5(:n10::text) || md5(:n11::text) || md5(:n12::text) || md5(:n13::text) || md5(:n14::text) || md5(:n15::text) || md5(:n16::text) || md5(:n17::text) || md5(:n18::text) || md5(:n19::text) || md5(:n20::text)
WHERE id IN (:n1, :n2, :n3, :n4, :n5, :n6, :n7, :n8, :n9, :n10, :n11, :n12, :n13, :n14, :n15, :n16, :n17, :n18, :n19, :n20);
COMMIT;
