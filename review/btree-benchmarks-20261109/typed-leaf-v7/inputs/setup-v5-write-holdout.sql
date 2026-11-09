\set ON_ERROR_STOP on
-- Separate fresh identical physical seed for holdout; not appended to frozen old ranking.
CREATE SEQUENCE h_write_i4_seq START 100001;
CREATE TABLE h_write_i4(k int PRIMARY KEY,pad text);
INSERT INTO h_write_i4 SELECT g,repeat('w',32) FROM generate_series(1,100000)g;
CREATE SEQUENCE h_write_i8_seq START 100001;
CREATE TABLE h_write_i8(k bigint PRIMARY KEY,pad text);
INSERT INTO h_write_i8 SELECT g,repeat('w',32) FROM generate_series(1,100000)g;
VACUUM(ANALYZE,FREEZE)h_write_i4;
VACUUM(ANALYZE,FREEZE)h_write_i8;
-- nextval is positive, bigint multiplication precedes modulo; gcd(7919,10000000)=1.
-- New keys are at least200000 and exceed the initial100000 and remain unique for any bounded run of10million consecutive sequence values.
-- Use bounded <1million values per table for warmups/timing/repeats, no fixed-wall profile writes.
-- Permuted destinations intentionally defeat the rightmost-leaf append cache for most inserts.
