-- Test mdb_superuser as pg_database_owner when datdba is a non-superuser.
--
-- has_privs_of_role(member, pg_database_owner) is true for mdb_superuser
-- members, but only when the database owner (datdba) is not a superuser
-- and not a "dangerous" role (pg_read_all_data, pg_write_all_data, etc).
-- The existing mdb_superuser.sql test creates a database owned by a
-- non-superuser (regress_mdb_superuser_user2), but only uses it for
-- GRANT/ALTER OWNER tests.  Here we verify that mdb_superuser can act as
-- pg_database_owner in that database — specifically, DROP tables owned
-- by the database owner.

CREATE ROLE regress_pgdbowner_dba;
CREATE ROLE regress_pgdbowner_su;
CREATE ROLE regress_pgdbowner_plain;

GRANT mdb_superuser TO regress_pgdbowner_su;
GRANT CREATE ON DATABASE regression TO regress_pgdbowner_plain;

-- Create a database owned by a non-superuser.
CREATE DATABASE regress_pgdbowner_db OWNER regress_pgdbowner_dba;

\c regress_pgdbowner_db

-- The DB owner creates a table.
SET ROLE regress_pgdbowner_dba;
CREATE TABLE regress_pgdbowner_t1(data text);
INSERT INTO regress_pgdbowner_t1 VALUES ('owner_data');
RESET SESSION AUTHORIZATION;

-- A plain role cannot drop the table.
SET ROLE regress_pgdbowner_plain;
DROP TABLE regress_pgdbowner_t1;
RESET SESSION AUTHORIZATION;

-- mdb_superuser can drop the table because has_privs_of_role(mdb_superuser,
-- pg_database_owner) is true, and pg_database_owner = regress_pgdbowner_dba
-- (which is not a superuser or dangerous role).
SET ROLE regress_pgdbowner_su;
DROP TABLE regress_pgdbowner_t1;
RESET SESSION AUTHORIZATION;

-- Verify the table is gone.
SELECT count(*) FROM pg_tables WHERE tablename = 'regress_pgdbowner_t1';

\c regression
DROP DATABASE regress_pgdbowner_db;

REVOKE mdb_superuser FROM regress_pgdbowner_su;
REVOKE CREATE ON DATABASE regression FROM regress_pgdbowner_plain;
DROP ROLE regress_pgdbowner_dba;
DROP ROLE regress_pgdbowner_su;
DROP ROLE regress_pgdbowner_plain;
