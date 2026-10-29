SELECT current_setting('max_prepared_transactions')::integer < 2 AS skip_test \gset
\if :skip_test
\quit
\endif

--
-- PREPARED TRANSACTIONS (two-phase commit)
--
-- We can't readily test persistence of prepared xacts within the
-- regression script framework, unfortunately.  Note that a crash
-- isn't really needed ... stopping and starting the postmaster would
-- be enough, but we can't even do that here.


-- create a simple table that we'll use in the tests
CREATE TABLE pxtest1 (foobar VARCHAR(10));

INSERT INTO pxtest1 VALUES ('aaa');


-- Test PREPARE TRANSACTION
BEGIN TRANSACTION ISOLATION LEVEL SERIALIZABLE;
UPDATE pxtest1 SET foobar = 'bbb' WHERE foobar = 'aaa';
SELECT * FROM pxtest1;
PREPARE TRANSACTION 'foo1';

SELECT * FROM pxtest1;

-- Test pg_prepared_xacts system view
SELECT gid FROM pg_prepared_xacts;

-- Test ROLLBACK PREPARED
ROLLBACK PREPARED 'foo1';

SELECT * FROM pxtest1;

SELECT gid FROM pg_prepared_xacts;


-- Test COMMIT PREPARED
BEGIN TRANSACTION ISOLATION LEVEL SERIALIZABLE;
INSERT INTO pxtest1 VALUES ('ddd');
SELECT * FROM pxtest1;
PREPARE TRANSACTION 'foo2';

SELECT * FROM pxtest1;

COMMIT PREPARED 'foo2';

SELECT * FROM pxtest1;

-- Test duplicate gids
BEGIN TRANSACTION ISOLATION LEVEL SERIALIZABLE;
UPDATE pxtest1 SET foobar = 'eee' WHERE foobar = 'ddd';
SELECT * FROM pxtest1;
PREPARE TRANSACTION 'foo3';

SELECT gid FROM pg_prepared_xacts;

BEGIN TRANSACTION ISOLATION LEVEL SERIALIZABLE;
INSERT INTO pxtest1 VALUES ('fff');

-- This should fail, because the gid foo3 is already in use
PREPARE TRANSACTION 'foo3';

SELECT * FROM pxtest1;

ROLLBACK PREPARED 'foo3';

SELECT * FROM pxtest1;

-- Test serialization failure (SSI)
BEGIN TRANSACTION ISOLATION LEVEL SERIALIZABLE;
UPDATE pxtest1 SET foobar = 'eee' WHERE foobar = 'ddd';
SELECT * FROM pxtest1;
PREPARE TRANSACTION 'foo4';

SELECT gid FROM pg_prepared_xacts;

BEGIN TRANSACTION ISOLATION LEVEL SERIALIZABLE;
SELECT * FROM pxtest1;

-- This should fail, because the two transactions have a write-skew anomaly
INSERT INTO pxtest1 VALUES ('fff');
PREPARE TRANSACTION 'foo5';

SELECT gid FROM pg_prepared_xacts;

ROLLBACK PREPARED 'foo4';

SELECT gid FROM pg_prepared_xacts;

-- Clean up
DROP TABLE pxtest1;

-- Test detection of session-level and xact-level locks on same object
BEGIN;
SELECT pg_advisory_lock(1);
SELECT pg_advisory_xact_lock_shared(1);
PREPARE TRANSACTION 'foo6';  -- fails

-- Test subtransactions
BEGIN TRANSACTION ISOLATION LEVEL SERIALIZABLE;
  CREATE TABLE pxtest2 (a int);
  INSERT INTO pxtest2 VALUES (1);
  SAVEPOINT a;
    INSERT INTO pxtest2 VALUES (2);
  ROLLBACK TO a;
  SAVEPOINT b;
  INSERT INTO pxtest2 VALUES (3);
PREPARE TRANSACTION 'regress-one';

CREATE TABLE pxtest3(fff int);

-- Test shared invalidation
BEGIN TRANSACTION ISOLATION LEVEL SERIALIZABLE;
  DROP TABLE pxtest3;
  CREATE TABLE pxtest4 (a int);
  INSERT INTO pxtest4 VALUES (1);
  INSERT INTO pxtest4 VALUES (2);
  DECLARE foo CURSOR FOR SELECT * FROM pxtest4;
  -- Fetch 1 tuple, keeping the cursor open
  FETCH 1 FROM foo;
PREPARE TRANSACTION 'regress-two';

-- No such cursor
FETCH 1 FROM foo;

-- Table doesn't exist, the creation hasn't been committed yet
SELECT * FROM pxtest2;

-- There should be two prepared transactions
SELECT gid FROM pg_prepared_xacts;

-- pxtest3 should be locked because of the pending DROP
begin;
lock table pxtest3 in access share mode nowait;
rollback;

-- Disconnect, we will continue testing in a different backend
\c -

-- There should still be two prepared transactions
SELECT gid FROM pg_prepared_xacts;

-- pxtest3 should still be locked because of the pending DROP
begin;
lock table pxtest3 in access share mode nowait;
rollback;

-- Commit table creation
COMMIT PREPARED 'regress-one';
\d pxtest2
SELECT * FROM pxtest2;

-- There should be one prepared transaction
SELECT gid FROM pg_prepared_xacts;

-- Commit table drop
COMMIT PREPARED 'regress-two';
SELECT * FROM pxtest3;

-- There should be no prepared transactions
SELECT gid FROM pg_prepared_xacts;

-- Clean up
DROP TABLE pxtest2;
-- pxtest3 was already dropped
DROP TABLE pxtest4;

-- Prepared transaction ownership follows inherited role privileges.
CREATE ROLE regress_prepare_owner;
CREATE ROLE regress_prepare_member;
CREATE ROLE regress_prepare_indirect;
CREATE ROLE regress_prepare_noinherit NOINHERIT;
CREATE ROLE regress_prepare_other;
GRANT regress_prepare_owner TO regress_prepare_member;
GRANT regress_prepare_member TO regress_prepare_indirect;
GRANT regress_prepare_owner TO regress_prepare_noinherit;
CREATE TABLE pxtest_inherit (a int);
GRANT INSERT ON pxtest_inherit TO regress_prepare_owner;

-- The preparing role can still finish its own transactions.
SET ROLE regress_prepare_owner;
BEGIN;
INSERT INTO pxtest_inherit VALUES (0);
PREPARE TRANSACTION 'regress_inherit_commit';
COMMIT PREPARED 'regress_inherit_commit';
BEGIN;
INSERT INTO pxtest_inherit VALUES (1);
PREPARE TRANSACTION 'regress_inherit_rollback';
ROLLBACK PREPARED 'regress_inherit_rollback';

BEGIN;
INSERT INTO pxtest_inherit VALUES (2);
PREPARE TRANSACTION 'regress_inherit_commit';
BEGIN;
INSERT INTO pxtest_inherit VALUES (3);
PREPARE TRANSACTION 'regress_inherit_rollback';
RESET ROLE;

-- Unrelated roles and non-inheriting memberships do not confer ownership.
SET ROLE regress_prepare_other;
COMMIT PREPARED 'regress_inherit_commit';  -- fails
ROLLBACK PREPARED 'regress_inherit_rollback';  -- fails
RESET ROLE;
SET ROLE regress_prepare_noinherit;
COMMIT PREPARED 'regress_inherit_commit';  -- fails
ROLLBACK PREPARED 'regress_inherit_rollback';  -- fails
RESET ROLE;

-- Inherited privileges suffice without SET ROLE.
SET ROLE regress_prepare_member;
SELECT pg_has_role(current_user, 'regress_prepare_owner', 'USAGE') AS inherit;
COMMIT PREPARED 'regress_inherit_commit';
ROLLBACK PREPARED 'regress_inherit_rollback';
RESET ROLE;

-- Indirect inheritance works as well.
SET ROLE regress_prepare_owner;
BEGIN;
INSERT INTO pxtest_inherit VALUES (4);
PREPARE TRANSACTION 'regress_inherit_commit';
BEGIN;
INSERT INTO pxtest_inherit VALUES (5);
PREPARE TRANSACTION 'regress_inherit_rollback';
RESET ROLE;
SET ROLE regress_prepare_indirect;
COMMIT PREPARED 'regress_inherit_commit';
ROLLBACK PREPARED 'regress_inherit_rollback';
RESET ROLE;

-- Revoking and restoring the grant invalidates cached privileges.
SET ROLE regress_prepare_owner;
BEGIN;
INSERT INTO pxtest_inherit VALUES (6);
PREPARE TRANSACTION 'regress_inherit_commit';
BEGIN;
INSERT INTO pxtest_inherit VALUES (7);
PREPARE TRANSACTION 'regress_inherit_rollback';
RESET ROLE;
REVOKE regress_prepare_owner FROM regress_prepare_member;
SET ROLE regress_prepare_member;
COMMIT PREPARED 'regress_inherit_commit';  -- fails after REVOKE
ROLLBACK PREPARED 'regress_inherit_rollback';  -- fails after REVOKE
RESET ROLE;
GRANT regress_prepare_owner TO regress_prepare_member;
SET ROLE regress_prepare_member;
COMMIT PREPARED 'regress_inherit_commit';
ROLLBACK PREPARED 'regress_inherit_rollback';
RESET ROLE;

-- A non-inheriting member can explicitly become the preparing role.
SET ROLE regress_prepare_owner;
BEGIN;
INSERT INTO pxtest_inherit VALUES (8);
PREPARE TRANSACTION 'regress_inherit_commit';
BEGIN;
INSERT INTO pxtest_inherit VALUES (9);
PREPARE TRANSACTION 'regress_inherit_rollback';
RESET ROLE;
SET ROLE regress_prepare_noinherit;
SET ROLE regress_prepare_owner;
COMMIT PREPARED 'regress_inherit_commit';
ROLLBACK PREPARED 'regress_inherit_rollback';
RESET ROLE;

-- Superusers retain their existing ability to finish any transaction.
SET ROLE regress_prepare_owner;
BEGIN;
INSERT INTO pxtest_inherit VALUES (10);
PREPARE TRANSACTION 'regress_inherit_commit';
BEGIN;
INSERT INTO pxtest_inherit VALUES (11);
PREPARE TRANSACTION 'regress_inherit_rollback';
RESET ROLE;
COMMIT PREPARED 'regress_inherit_commit';
ROLLBACK PREPARED 'regress_inherit_rollback';

-- Membership in an unrelated ordinary role does not grant superuser powers.
BEGIN;
INSERT INTO pxtest_inherit VALUES (12);
PREPARE TRANSACTION 'regress_inherit_commit';
BEGIN;
INSERT INTO pxtest_inherit VALUES (13);
PREPARE TRANSACTION 'regress_inherit_rollback';
SET ROLE regress_prepare_member;
COMMIT PREPARED 'regress_inherit_commit';  -- fails
ROLLBACK PREPARED 'regress_inherit_rollback';  -- fails
RESET ROLE;
COMMIT PREPARED 'regress_inherit_commit';
ROLLBACK PREPARED 'regress_inherit_rollback';

SELECT * FROM pxtest_inherit ORDER BY a;
SELECT gid FROM pg_prepared_xacts WHERE gid LIKE 'regress_inherit_%';

DROP TABLE pxtest_inherit;
DROP ROLE regress_prepare_other;
DROP ROLE regress_prepare_noinherit;
DROP ROLE regress_prepare_indirect;
DROP ROLE regress_prepare_member;
DROP ROLE regress_prepare_owner;
