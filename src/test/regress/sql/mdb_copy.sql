CREATE ROLE regress_mdb_copy_r1 LOGIN NOSUPERUSER;
CREATE ROLE regress_mdb_copy_r1_mdb_adm LOGIN NOSUPERUSER;
GRANT mdb_admin TO regress_mdb_copy_r1_mdb_adm;
CREATE ROLE regress_mdb_copy_r1_su LOGIN SUPERUSER;

-- should fail
SET ROLE regress_mdb_copy_r1;

CREATE TABLE tt(i int);
COPY tt FROM PROGRAM '/bin/bash';
DROP TABLE tt;

-- should fail
SET ROLE regress_mdb_copy_r1_mdb_adm;

CREATE TABLE tt(i int);
COPY tt FROM PROGRAM '/bin/bash';
DROP TABLE tt;

-- fail, no one can do it
SET ROLE regress_mdb_copy_r1_su;

CREATE TABLE tt(i int);
COPY tt FROM PROGRAM '/bin/bash';
DROP TABLE tt;

RESET SESSION AUTHORIZATION;

DROP ROLE regress_mdb_copy_r1;
DROP ROLE regress_mdb_copy_r1_mdb_adm;
DROP ROLE regress_mdb_copy_r1_su;
