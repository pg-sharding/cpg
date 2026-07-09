

--
-- bt_index_check()
--
CREATE FUNCTION bt_index_check(index regclass,
    heapallindexed boolean, checkhot bool)
RETURNS VOID
AS 'MODULE_PATHNAME', 'bt_index_check'
LANGUAGE C STRICT PARALLEL RESTRICTED;

--
-- bt_index_parent_check()
--
CREATE FUNCTION bt_index_parent_check(index regclass,
    heapallindexed boolean, rootdescend boolean, checkhot bool)
RETURNS VOID
AS 'MODULE_PATHNAME', 'bt_index_parent_check'
LANGUAGE C STRICT PARALLEL RESTRICTED;


-- Don't want these to be available to public
REVOKE ALL ON FUNCTION bt_index_check(regclass, boolean) FROM PUBLIC;
REVOKE ALL ON FUNCTION bt_index_parent_check(regclass, boolean) FROM PUBLIC;