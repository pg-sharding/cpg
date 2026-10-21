/* contrib/amcheck/amcheck--1.4--1.5.sql */

-- complain if script is sourced in psql, rather than via CREATE EXTENSION
\echo Use "ALTER EXTENSION amcheck UPDATE TO '1.5'" to load this file. \quit

--
-- bt_index_check()
--
-- Add indexallkeysmatch parameter to bt_index_check and bt_index_parent_check
CREATE FUNCTION bt_index_check(index regclass,
    heapallindexed boolean, checkhot boolean, keepgoing boolean,
    indexallkeysmatch boolean)
RETURNS VOID
AS 'MODULE_PATHNAME', 'bt_index_check'
LANGUAGE C STRICT PARALLEL RESTRICTED;

--
-- bt_index_parent_check()
--
CREATE FUNCTION bt_index_parent_check(index regclass,
    heapallindexed boolean, rootdescend boolean, checkhot boolean,
    keepgoing boolean, indexallkeysmatch boolean)
RETURNS VOID
AS 'MODULE_PATHNAME', 'bt_index_parent_check'
LANGUAGE C STRICT PARALLEL RESTRICTED;

-- Don't want these to be available to public
REVOKE ALL ON FUNCTION bt_index_check(regclass, boolean, boolean, boolean, boolean) FROM PUBLIC;
REVOKE ALL ON FUNCTION bt_index_parent_check(regclass, boolean, boolean, boolean, boolean, boolean) FROM PUBLIC;
