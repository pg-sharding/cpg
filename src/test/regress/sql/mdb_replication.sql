CREATE ROLE regress_mdb_repl_no_priv LOGIN NOSUPERUSER;
CREATE ROLE regress_mdb_repl_no_priv2 LOGIN NOSUPERUSER;
CREATE ROLE regress_mdb_repl LOGIN NOSUPERUSER;
CREATE ROLE regress_mdb_repl_su LOGIN SUPERUSER;
CREATE ROLE regress_mdb_repl_pgrad LOGIN NOSUPERUSER;

GRANT pg_read_all_data TO regress_mdb_repl_pgrad;

GRANT mdb_admin to regress_mdb_repl;

GRANT CREATE ON DATABASE REGRESSION TO regress_mdb_repl;

GRANT CREATE ON DATABASE REGRESSION TO regress_mdb_repl_no_priv;

-- ok - member of mdb_admin
SET SESSION AUTHORIZATION regress_mdb_repl;
CREATE SUBSCRIPTION regress_mdbsub CONNECTION 'dbname=doesnotexist password=regress_fakepassword' PUBLICATION foo WITH (slot_name = NONE, connect = false);

-- ok - we are allowed to change ownership under mdb_admin
ALTER SUBSCRIPTION regress_mdbsub OWNER TO regress_mdb_repl_no_priv2;

-- should fail - we are not allowed to change ownership to priviledged role
ALTER SUBSCRIPTION regress_mdbsub OWNER TO regress_mdb_repl_su;
ALTER SUBSCRIPTION regress_mdbsub OWNER TO regress_mdb_repl_pgrad;

RESET SESSION AUTHORIZATION;
DROP SUBSCRIPTION regress_mdbsub;

-- should fail - not member of pg_subcription_users or mdb_admin 
SET SESSION AUTHORIZATION regress_mdb_repl_no_priv;
CREATE SUBSCRIPTION regress_mdbsub_no_priv CONNECTION 'dbname=doesnotexist password=regress_fakepassword' PUBLICATION foo WITH (slot_name = NONE, connect = false);
-- reset to su, cleanup

RESET SESSION AUTHORIZATION;

REVOKE ALL ON DATABASE REGRESSION FROM regress_mdb_repl;
REVOKE ALL ON DATABASE REGRESSION FROM regress_mdb_repl_no_priv;

DROP ROLE regress_mdb_repl;
DROP ROLE regress_mdb_repl_no_priv;
DROP ROLE regress_mdb_repl_no_priv2;