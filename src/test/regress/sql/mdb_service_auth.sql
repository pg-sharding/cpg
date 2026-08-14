-- Test that mdb_service_auth owner is considered "dangerous" by mdb_superuser.
--
-- has_privs_of_unwanted_system_role() checks if the target role (object
-- owner) is a member of mdb_service_auth (rule #7).  If so, the mdb_superuser
-- bypass in has_privs_of_role() returns false — mdb_superuser cannot act
-- as that owner.  This test verifies that rule #7 is enforced.

-- mdb_service_auth should already exist (created by test_setup or MDB init).
-- Verify it exists; if not, skip the test gracefully.
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'mdb_service_auth') THEN
        CREATE ROLE mdb_service_auth NOLOGIN;
    END IF;
END $$;

CREATE ROLE regress_svcauth_dangerous;
CREATE ROLE regress_svcauth_su;
CREATE ROLE regress_svcauth_plain;

GRANT CREATE ON DATABASE regression TO regress_svcauth_dangerous;
GRANT CREATE ON DATABASE regression TO regress_svcauth_su;
GRANT CREATE ON DATABASE regression TO regress_svcauth_plain;

-- Make the "dangerous" role a member of mdb_service_auth.
GRANT mdb_service_auth TO regress_svcauth_dangerous;

-- The dangerous role creates a table in its own schema.
SET ROLE regress_svcauth_dangerous;
CREATE SCHEMA regress_svcauth_schema;
CREATE TABLE regress_svcauth_schema.t1(data text);
INSERT INTO regress_svcauth_schema.t1 VALUES ('dangerous_data');
RESET SESSION AUTHORIZATION;

-- A plain role cannot read or drop the table.
SET ROLE regress_svcauth_plain;
SELECT * FROM regress_svcauth_schema.t1;
DROP TABLE regress_svcauth_schema.t1;
RESET SESSION AUTHORIZATION;

-- Grant mdb_superuser to the su role.
GRANT mdb_superuser TO regress_svcauth_su;

-- mdb_superuser CANNOT bypass ownership for a table owned by a role that
-- is a member of mdb_service_auth (rule #7: has_privs_of_unwanted_system_role
-- returns true, so the mdb_superuser bypass returns false).
-- The table is in the dangerous role's own schema, so DROP cannot go
-- through schema ownership either.
SET ROLE regress_svcauth_su;
SELECT * FROM regress_svcauth_schema.t1;
DROP TABLE regress_svcauth_schema.t1;
RESET SESSION AUTHORIZATION;

-- Verify the table still exists.
SELECT count(*) FROM pg_tables WHERE tablename = 't1' AND schemaname = 'regress_svcauth_schema';

-- Cleanup
DROP TABLE regress_svcauth_schema.t1;
DROP SCHEMA regress_svcauth_schema;
REVOKE mdb_service_auth FROM regress_svcauth_dangerous;
REVOKE CREATE ON DATABASE regression FROM regress_svcauth_dangerous;
REVOKE CREATE ON DATABASE regression FROM regress_svcauth_su;
REVOKE CREATE ON DATABASE regression FROM regress_svcauth_plain;
REVOKE mdb_superuser FROM regress_svcauth_su;
DROP ROLE regress_svcauth_dangerous;
DROP ROLE regress_svcauth_su;
DROP ROLE regress_svcauth_plain;
