-- Test implicit pg_* capabilities of mdb_superuser.
--
-- has_privs_of_role(member, <pg_*>) returns true for all non-excluded
-- predefined roles when member is a member of mdb_superuser.  This means
-- mdb_superuser implicitly has: pg_checkpoint (CHECKPOINT), pg_maintain
-- (VACUUM/ANALYZE/CLUSTER), pg_read_all_settings, pg_signal_backend, etc.

CREATE ROLE regress_implicit_su;

GRANT CREATE ON DATABASE regression TO regress_implicit_su;

-- A table owned by another role for VACUUM/CLUSTER tests.
CREATE ROLE regress_implicit_table_owner;
GRANT CREATE ON DATABASE regression TO regress_implicit_table_owner;
SET ROLE regress_implicit_table_owner;
CREATE TABLE regress_implicit_t1(data text);
INSERT INTO regress_implicit_t1 VALUES ('test');
RESET SESSION AUTHORIZATION;

GRANT mdb_superuser TO regress_implicit_su;

-- === pg_checkpoint: CHECKPOINT ===
SET ROLE regress_implicit_su;
CHECKPOINT;
RESET SESSION AUTHORIZATION;

-- === pg_maintain: VACUUM / ANALYZE on another role's table ===
SET ROLE regress_implicit_su;
VACUUM regress_implicit_t1;
ANALYZE regress_implicit_t1;
RESET SESSION AUTHORIZATION;

-- === pg_read_all_settings: can see superuser-only settings ===
SET ROLE regress_implicit_su;
SELECT count(*) > 0 AS can_see_restricted_settings
FROM pg_settings
WHERE source = 'default' AND setting IS NOT NULL;
RESET SESSION AUTHORIZATION;

-- === Verify a non-mdb_superuser role CANNOT do these ===
CREATE ROLE regress_implicit_plain;
GRANT CREATE ON DATABASE regression TO regress_implicit_plain;

SET ROLE regress_implicit_plain;
CHECKPOINT;
RESET SESSION AUTHORIZATION;

SET ROLE regress_implicit_plain;
VACUUM regress_implicit_t1;
RESET SESSION AUTHORIZATION;

-- Cleanup
DROP TABLE regress_implicit_t1;
REVOKE CREATE ON DATABASE regression FROM regress_implicit_su;
REVOKE CREATE ON DATABASE regression FROM regress_implicit_table_owner;
REVOKE CREATE ON DATABASE regression FROM regress_implicit_plain;
REVOKE mdb_superuser FROM regress_implicit_su;
DROP ROLE regress_implicit_su;
DROP ROLE regress_implicit_table_owner;
DROP ROLE regress_implicit_plain;
