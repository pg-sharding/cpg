\set ON_ERROR_STOP on
\pset format unaligned
\pset tuples_only on
SET jit=off;SET max_parallel_workers_per_gather=0;
SELECT pg_is_in_recovery();
SELECT typed_sweep('typed_perm','recovery-permanent');
SELECT typed_sweep('typed_null_first','recovery-nulls-first');
SELECT typed_ref('recovery-rescan','SELECT sum((SELECT count(*) FROM typed_perm WHERE k=g))::text FROM unnest(ARRAY[-30000,3,4,NULL,30000]::bigint[])g');
SELECT 'recovery-targets:ok';
