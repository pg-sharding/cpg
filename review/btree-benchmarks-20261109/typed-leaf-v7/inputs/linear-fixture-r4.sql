\set ON_ERROR_STOP on
SET jit=off;
SET max_parallel_workers_per_gather=0;
SET statement_timeout='90s';
CREATE TABLE q(k bigint,v bigint);
INSERT INTO q SELECT g,g FROM generate_series(-20000,20000)g;
INSERT INTO q SELECT 3,g FROM generate_series(1,60000)g;
INSERT INTO q VALUES('-9223372036854775808',1),('9223372036854775807',2),(NULL,3);
CREATE INDEX q_idx ON q(k);
CREATE INDEX q_desc_idx ON q(k DESC NULLS FIRST);
CREATE INDEX q_include_idx ON q(k) INCLUDE(v);
CREATE INDEX q_multi_idx ON q(k,v);
CREATE DOMAIN q_domain AS bigint;
CREATE TABLE qd(k q_domain);
INSERT INTO qd SELECT k FROM q;
CREATE INDEX qd_idx ON qd(k);
VACUUM(ANALYZE)q;
VACUUM(ANALYZE)qd;
