/* contrib/pg_target_promote/pg_target_promote--1.0.sql */

-- complain if script is sourced in psql, rather than via CREATE EXTENSION
\echo Use "CREATE EXTENSION pg_target_promote" to load this file. \quit

CREATE FUNCTION pg_bump_timeline()
RETURNS void
AS 'MODULE_PATHNAME', 'pg_bump_timeline'
LANGUAGE C STRICT VOLATILE PARALLEL SAFE;

REVOKE EXECUTE ON FUNCTION pg_bump_timeline() FROM public;
