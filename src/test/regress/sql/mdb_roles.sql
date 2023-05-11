CREATE ROLE regress_mdb_roles_user1;
CREATE ROLE regress_mdb_roles_user2;


GRANT mdb_admin, mdb_superuser TO regress_mdb_roles_user1 WITH ADMIN OPTION;

GRANT CREATE ON DATABASE regression TO regress_mdb_roles_user1;

SET ROLE regress_mdb_roles_user1;

CREATE TABLE t();

ALTER TABLE t OWNER TO mdb_admin; --ok
ALTER TABLE t OWNER TO mdb_superuser; --ok
ALTER TABLE t OWNER TO mdb_replication; --ok
ALTER TABLE t OWNER TO mdb_service_auth; --should fail

GRANT mdb_service_auth to regress_mdb_roles_user1;
GRANT mdb_service_auth to regress_mdb_roles_user2;

GRANT mdb_superuser to regress_mdb_roles_user1;
GRANT mdb_superuser to regress_mdb_roles_user2;


-- cleanup

RESET SESSION AUTHORIZATION;


REVOKE CREATE ON DATABASE regression FROM regress_mdb_roles_user1;

DROP TABLE t;
DROP ROLE regress_mdb_roles_user1;
DROP ROLE regress_mdb_roles_user2;