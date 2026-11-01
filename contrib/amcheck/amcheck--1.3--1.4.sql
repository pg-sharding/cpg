/* contrib/amcheck/amcheck--1.3--1.4.sql */

-- complain if script is sourced in psql, rather than via CREATE EXTENSION
\echo Use "ALTER EXTENSION amcheck UPDATE TO '1.4'" to load this file. \quit


-- hash_index_check()
--
CREATE FUNCTION hash_index_check(index regclass)
RETURNS VOID
AS 'MODULE_PATHNAME', 'hash_index_check'
LANGUAGE C STRICT;

REVOKE ALL ON FUNCTION hash_index_check(regclass) FROM PUBLIC;
