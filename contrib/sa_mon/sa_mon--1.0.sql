/* contrib/sa_mon/sa_mon--1.0.sql */

-- complain if script is sourced in psql, rather than via CREATE EXTENSION
\echo Use "CREATE EXTENSION sa_mon" to load this file. \quit

CREATE FUNCTION mdb_get_sa_info()
RETURNS text
AS 'MODULE_PATHNAME', 'mdb_get_sa_info'
LANGUAGE C STRICT PARALLEL SAFE;

REVOKE ALL ON FUNCTION mdb_get_sa_info() FROM PUBLIC;
GRANT EXECUTE ON FUNCTION mdb_get_sa_info() TO pg_monitor;
