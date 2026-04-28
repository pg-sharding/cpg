CREATE ROLE regress_mdb_admin_user1;

CREATE ROLE mdb_superuser;
CREATE ROLE mdb_admin;

GRANT mdb_admin TO regress_mdb_admin_user1;
GRANT mdb_superuser TO regress_mdb_admin_user1;

GRANT CREATE ON DATABASE contrib_regression TO regress_mdb_admin_user1;

SET ROLE regress_mdb_admin_user1;

CREATE EXTENSION test_ext_mdb;

RESET ROLE;

DROP ROLE mdb_superuser;
DROP ROLE mdb_admin;

DROP OWNED BY regress_mdb_admin_user1;

DROP ROLE regress_mdb_admin_user1;
