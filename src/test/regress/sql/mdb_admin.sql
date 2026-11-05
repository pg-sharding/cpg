CREATE ROLE regress_mdb_admin_user1;
CREATE ROLE regress_mdb_admin_user2;
CREATE ROLE regress_mdb_admin_user3;

CREATE ROLE regress_superuser WITH SUPERUSER;
CREATE ROLE regress_repl_admin WITH REPLICATION;
CREATE ROLE regress_bypassrls_admin WITH BYPASSRLS;
CREATE ROLE regress_member_of_repl_admin;
GRANT regress_repl_admin TO regress_member_of_repl_admin;
CREATE ROLE regress_set_member_of_repl_admin;
CREATE ROLE regress_noset_member_of_repl_admin;
GRANT regress_repl_admin TO regress_set_member_of_repl_admin WITH INHERIT FALSE, SET TRUE;
GRANT regress_repl_admin TO regress_noset_member_of_repl_admin WITH INHERIT TRUE, SET FALSE;

GRANT mdb_admin TO regress_mdb_admin_user1;
GRANT CREATE ON DATABASE regression TO regress_mdb_admin_user2;
GRANT CREATE ON DATABASE regression TO regress_mdb_admin_user3;

-- mdb admin trasfers ownership to another role

SET ROLE regress_mdb_admin_user2;
CREATE FUNCTION regress_mdb_admin_add(integer, integer) RETURNS integer
    AS 'SELECT $1 + $2;'
    LANGUAGE SQL
    IMMUTABLE
    RETURNS NULL ON NULL INPUT;

CREATE SCHEMA regress_mdb_admin_schema;
GRANT CREATE ON SCHEMA regress_mdb_admin_schema TO regress_mdb_admin_user3;
CREATE TABLE regress_mdb_admin_schema.regress_mdb_admin_table();
CREATE TABLE regress_mdb_admin_table();
CREATE VIEW regress_mdb_admin_view as SELECT 1;
SET ROLE regress_mdb_admin_user1;

ALTER FUNCTION regress_mdb_admin_add (integer, integer) OWNER TO regress_mdb_admin_user3;
ALTER VIEW regress_mdb_admin_view OWNER TO regress_mdb_admin_user3;
ALTER TABLE regress_mdb_admin_schema.regress_mdb_admin_table OWNER TO regress_mdb_admin_user3;
ALTER TABLE regress_mdb_admin_table OWNER TO regress_mdb_admin_user3;
ALTER SCHEMA regress_mdb_admin_schema OWNER TO regress_mdb_admin_user3;


-- mdb admin fails to transfer ownership to superusers and particular system roles

ALTER FUNCTION regress_mdb_admin_add (integer, integer) OWNER TO regress_superuser;
ALTER VIEW regress_mdb_admin_view OWNER TO regress_superuser;
ALTER TABLE regress_mdb_admin_schema.regress_mdb_admin_table OWNER TO regress_superuser;
ALTER TABLE regress_mdb_admin_table OWNER TO regress_superuser;
ALTER SCHEMA regress_mdb_admin_schema OWNER TO regress_superuser;

ALTER FUNCTION regress_mdb_admin_add (integer, integer) OWNER TO pg_execute_server_program;
ALTER VIEW regress_mdb_admin_view OWNER TO pg_execute_server_program;
ALTER TABLE regress_mdb_admin_schema.regress_mdb_admin_table OWNER TO pg_execute_server_program;
ALTER TABLE regress_mdb_admin_table OWNER TO pg_execute_server_program;
ALTER SCHEMA regress_mdb_admin_schema OWNER TO pg_execute_server_program;

ALTER FUNCTION regress_mdb_admin_add (integer, integer) OWNER TO pg_write_server_files;
ALTER VIEW regress_mdb_admin_view OWNER TO pg_write_server_files;
ALTER TABLE regress_mdb_admin_schema.regress_mdb_admin_table OWNER TO pg_write_server_files;
ALTER TABLE regress_mdb_admin_table OWNER TO pg_write_server_files;
ALTER SCHEMA regress_mdb_admin_schema OWNER TO pg_write_server_files;

ALTER FUNCTION regress_mdb_admin_add (integer, integer) OWNER TO pg_read_server_files;
ALTER VIEW regress_mdb_admin_view OWNER TO pg_read_server_files;
ALTER TABLE regress_mdb_admin_schema.regress_mdb_admin_table OWNER TO pg_read_server_files;
ALTER TABLE regress_mdb_admin_table OWNER TO pg_read_server_files;
ALTER SCHEMA regress_mdb_admin_schema OWNER TO pg_read_server_files;

ALTER FUNCTION regress_mdb_admin_add (integer, integer) OWNER TO pg_write_all_data;
ALTER VIEW regress_mdb_admin_view OWNER TO pg_write_all_data;
ALTER TABLE regress_mdb_admin_schema.regress_mdb_admin_table OWNER TO pg_write_all_data;
ALTER TABLE regress_mdb_admin_table OWNER TO pg_write_all_data;
ALTER SCHEMA regress_mdb_admin_schema OWNER TO pg_write_all_data;

ALTER FUNCTION regress_mdb_admin_add (integer, integer) OWNER TO pg_read_all_data;
ALTER VIEW regress_mdb_admin_view OWNER TO pg_read_all_data;
ALTER TABLE regress_mdb_admin_schema.regress_mdb_admin_table OWNER TO pg_read_all_data;
ALTER TABLE regress_mdb_admin_table OWNER TO pg_read_all_data;
ALTER SCHEMA regress_mdb_admin_schema OWNER TO pg_read_all_data;

-- mdb admin fails to transfer ownership to roles with REPLICATION or
-- BYPASSRLS attributes, and to members of such roles

ALTER FUNCTION regress_mdb_admin_add (integer, integer) OWNER TO regress_repl_admin;
ALTER VIEW regress_mdb_admin_view OWNER TO regress_repl_admin;
ALTER TABLE regress_mdb_admin_schema.regress_mdb_admin_table OWNER TO regress_repl_admin;
ALTER TABLE regress_mdb_admin_table OWNER TO regress_repl_admin;
ALTER SCHEMA regress_mdb_admin_schema OWNER TO regress_repl_admin;

ALTER FUNCTION regress_mdb_admin_add (integer, integer) OWNER TO regress_bypassrls_admin;
ALTER VIEW regress_mdb_admin_view OWNER TO regress_bypassrls_admin;
ALTER TABLE regress_mdb_admin_schema.regress_mdb_admin_table OWNER TO regress_bypassrls_admin;
ALTER TABLE regress_mdb_admin_table OWNER TO regress_bypassrls_admin;
ALTER SCHEMA regress_mdb_admin_schema OWNER TO regress_bypassrls_admin;

ALTER FUNCTION regress_mdb_admin_add (integer, integer) OWNER TO regress_member_of_repl_admin;
ALTER VIEW regress_mdb_admin_view OWNER TO regress_member_of_repl_admin;
ALTER TABLE regress_mdb_admin_schema.regress_mdb_admin_table OWNER TO regress_member_of_repl_admin;
ALTER TABLE regress_mdb_admin_table OWNER TO regress_member_of_repl_admin;
ALTER SCHEMA regress_mdb_admin_schema OWNER TO regress_member_of_repl_admin;

-- any membership edge counts, even with INHERIT FALSE or SET FALSE:
-- the transfer must fail as well

ALTER FUNCTION regress_mdb_admin_add (integer, integer) OWNER TO regress_set_member_of_repl_admin;
ALTER VIEW regress_mdb_admin_view OWNER TO regress_set_member_of_repl_admin;
ALTER TABLE regress_mdb_admin_schema.regress_mdb_admin_table OWNER TO regress_set_member_of_repl_admin;
ALTER TABLE regress_mdb_admin_table OWNER TO regress_set_member_of_repl_admin;
ALTER SCHEMA regress_mdb_admin_schema OWNER TO regress_set_member_of_repl_admin;

ALTER FUNCTION regress_mdb_admin_add (integer, integer) OWNER TO regress_noset_member_of_repl_admin;
ALTER VIEW regress_mdb_admin_view OWNER TO regress_noset_member_of_repl_admin;
ALTER TABLE regress_mdb_admin_schema.regress_mdb_admin_table OWNER TO regress_noset_member_of_repl_admin;
ALTER TABLE regress_mdb_admin_table OWNER TO regress_noset_member_of_repl_admin;
ALTER SCHEMA regress_mdb_admin_schema OWNER TO regress_noset_member_of_repl_admin;

-- end tests

RESET SESSION AUTHORIZATION;
--
REVOKE CREATE ON DATABASE regression FROM regress_mdb_admin_user2;
REVOKE CREATE ON DATABASE regression FROM regress_mdb_admin_user3;

DROP VIEW regress_mdb_admin_view;
DROP FUNCTION regress_mdb_admin_add;
DROP TABLE regress_mdb_admin_schema.regress_mdb_admin_table;
DROP TABLE regress_mdb_admin_table;
DROP SCHEMA regress_mdb_admin_schema;
DROP ROLE regress_mdb_admin_user1;
DROP ROLE regress_mdb_admin_user2;
DROP ROLE regress_mdb_admin_user3;
DROP ROLE regress_superuser;
DROP ROLE regress_member_of_repl_admin;
DROP ROLE regress_set_member_of_repl_admin;
DROP ROLE regress_noset_member_of_repl_admin;
DROP ROLE regress_repl_admin;
DROP ROLE regress_bypassrls_admin;
