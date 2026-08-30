/* contrib/pg_target_promote/pg_target_promote--1.0.sql */

-- complain if script is sourced in psql, rather than via CREATE EXTENSION
\echo Use "CREATE EXTENSION pg_target_promote" to load this file. \quit

CREATE FUNCTION pg_target_promote(target_timeline integer,
                                  wait boolean DEFAULT true,
                                  wait_seconds integer DEFAULT 60)
RETURNS boolean
AS 'MODULE_PATHNAME', 'pg_target_promote_proxy'
LANGUAGE C STRICT VOLATILE PARALLEL SAFE;

REVOKE EXECUTE ON FUNCTION pg_target_promote(integer, boolean, integer) FROM public;
