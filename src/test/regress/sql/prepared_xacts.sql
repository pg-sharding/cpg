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
PREPARE TRANSACTION 'regress_foo1';

SELECT * FROM pxtest1;

-- Test pg_prepared_xacts system view
SELECT gid FROM pg_prepared_xacts WHERE gid ~ '^regress_' ORDER BY gid;

-- Test ROLLBACK PREPARED
ROLLBACK PREPARED 'regress_foo1';

SELECT * FROM pxtest1;

SELECT gid FROM pg_prepared_xacts WHERE gid ~ '^regress_' ORDER BY gid;


-- Test COMMIT PREPARED
BEGIN TRANSACTION ISOLATION LEVEL SERIALIZABLE;
INSERT INTO pxtest1 VALUES ('ddd');
SELECT * FROM pxtest1;
PREPARE TRANSACTION 'regress_foo2';

SELECT * FROM pxtest1;

COMMIT PREPARED 'regress_foo2';

SELECT * FROM pxtest1;

-- Test duplicate gids
BEGIN TRANSACTION ISOLATION LEVEL SERIALIZABLE;
UPDATE pxtest1 SET foobar = 'eee' WHERE foobar = 'ddd';
SELECT * FROM pxtest1;
PREPARE TRANSACTION 'regress_foo3';

SELECT gid FROM pg_prepared_xacts WHERE gid ~ '^regress_' ORDER BY gid;

BEGIN TRANSACTION ISOLATION LEVEL SERIALIZABLE;
INSERT INTO pxtest1 VALUES ('fff');

-- This should fail, because the gid foo3 is already in use
PREPARE TRANSACTION 'regress_foo3';

SELECT * FROM pxtest1;

ROLLBACK PREPARED 'regress_foo3';

SELECT * FROM pxtest1;

-- Test serialization failure (SSI)
BEGIN TRANSACTION ISOLATION LEVEL SERIALIZABLE;
UPDATE pxtest1 SET foobar = 'eee' WHERE foobar = 'ddd';
SELECT * FROM pxtest1;
PREPARE TRANSACTION 'regress_foo4';

SELECT gid FROM pg_prepared_xacts WHERE gid ~ '^regress_' ORDER BY gid;

BEGIN TRANSACTION ISOLATION LEVEL SERIALIZABLE;
SELECT * FROM pxtest1;

-- This should fail, because the two transactions have a write-skew anomaly
INSERT INTO pxtest1 VALUES ('fff');
PREPARE TRANSACTION 'regress_foo5';

SELECT gid FROM pg_prepared_xacts WHERE gid ~ '^regress_' ORDER BY gid;

ROLLBACK PREPARED 'regress_foo4';

SELECT gid FROM pg_prepared_xacts WHERE gid ~ '^regress_' ORDER BY gid;

-- Clean up
DROP TABLE pxtest1;

-- Test detection of session-level and xact-level locks on same object
BEGIN;
SELECT pg_advisory_lock(1);
SELECT pg_advisory_xact_lock_shared(1);
PREPARE TRANSACTION 'regress_foo6';  -- fails

-- Test subtransactions
BEGIN TRANSACTION ISOLATION LEVEL SERIALIZABLE;
  CREATE TABLE pxtest2 (a int);
  INSERT INTO pxtest2 VALUES (1);
  SAVEPOINT a;
    INSERT INTO pxtest2 VALUES (2);
  ROLLBACK TO a;
  SAVEPOINT b;
  INSERT INTO pxtest2 VALUES (3);
PREPARE TRANSACTION 'regress_sub1';

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
PREPARE TRANSACTION 'regress_sub2';

-- No such cursor
FETCH 1 FROM foo;

-- Table doesn't exist, the creation hasn't been committed yet
SELECT * FROM pxtest2;

-- There should be two prepared transactions
SELECT gid FROM pg_prepared_xacts WHERE gid ~ '^regress_' ORDER BY gid;

-- pxtest3 should be locked because of the pending DROP
begin;
lock table pxtest3 in access share mode nowait;
rollback;

-- Disconnect, we will continue testing in a different backend
\c -

-- There should still be two prepared transactions
SELECT gid FROM pg_prepared_xacts WHERE gid ~ '^regress_' ORDER BY gid;

-- pxtest3 should still be locked because of the pending DROP
begin;
lock table pxtest3 in access share mode nowait;
rollback;

-- Commit table creation
COMMIT PREPARED 'regress_sub1';
\d pxtest2
SELECT * FROM pxtest2;

-- There should be one prepared transaction
SELECT gid FROM pg_prepared_xacts WHERE gid ~ '^regress_' ORDER BY gid;

-- Commit table drop
COMMIT PREPARED 'regress_sub2';
SELECT * FROM pxtest3;

-- There should be no prepared transactions
SELECT gid FROM pg_prepared_xacts WHERE gid ~ '^regress_' ORDER BY gid;


-- Test row-level locks held by prepared transactions
CREATE TABLE pxtest_rowlock (id int PRIMARY KEY, data text);
INSERT INTO pxtest_rowlock VALUES (1, 'test data');

BEGIN;
SELECT * FROM pxtest_rowlock WHERE id = 1 FOR SHARE;
PREPARE TRANSACTION 'regress_p1';

-- Should fail because the row is locked
SELECT * FROM pxtest_rowlock WHERE id = 1 FOR UPDATE NOWAIT;

-- Test prepared transactions that participate in multixacts. For
-- that, lock the same row again, creating a multixid.
BEGIN;
SELECT * FROM pxtest_rowlock WHERE id = 1 FOR SHARE;
PREPARE TRANSACTION 'regress_p2';

-- Should fail because the row is locked
SELECT * FROM pxtest_rowlock WHERE id = 1 FOR UPDATE NOWAIT;

ROLLBACK PREPARED 'regress_p1';
ROLLBACK PREPARED 'regress_p2';

-- Clean up
DROP TABLE pxtest2;
-- pxtest3 was already dropped
DROP TABLE pxtest4;
DROP TABLE pxtest_rowlock;

-- Test delegating prepared transaction completion to a transaction manager.
CREATE ROLE regress_prepare_owner;
CREATE ROLE regress_prepare_member IN ROLE regress_prepare_owner;
CREATE ROLE regress_prepare_manager;
CREATE ROLE regress_prepare_indirect IN ROLE regress_prepare_manager;
CREATE ROLE regress_prepare_noinherit;
GRANT pg_manage_prepared_xacts TO regress_prepare_noinherit WITH INHERIT FALSE;
CREATE TABLE pxtest_manage (a int);
GRANT INSERT ON pxtest_manage TO regress_prepare_owner;

-- The original owner can still commit and roll back its own transactions.
SET ROLE regress_prepare_owner;
BEGIN;
INSERT INTO pxtest_manage VALUES (0);
PREPARE TRANSACTION 'regress_manage_commit';
COMMIT PREPARED 'regress_manage_commit';
BEGIN;
INSERT INTO pxtest_manage VALUES (-1);
PREPARE TRANSACTION 'regress_manage_rollback';
ROLLBACK PREPARED 'regress_manage_rollback';

BEGIN;
INSERT INTO pxtest_manage VALUES (1);
PREPARE TRANSACTION 'regress_manage_commit';
BEGIN;
INSERT INTO pxtest_manage VALUES (2);
PREPARE TRANSACTION 'regress_manage_rollback';
RESET ROLE;

-- Inheriting the preparing user's privileges does not confer ownership.
SET ROLE regress_prepare_member;
COMMIT PREPARED 'regress_manage_commit';  -- fails
ROLLBACK PREPARED 'regress_manage_rollback';  -- fails
RESET ROLE;
SET ROLE regress_prepare_manager;
COMMIT PREPARED 'regress_manage_commit';  -- fails before GRANT
ROLLBACK PREPARED 'regress_manage_rollback';  -- fails before GRANT
RESET ROLE;

-- A non-inherited membership does not confer the privilege automatically.
SET ROLE regress_prepare_noinherit;
COMMIT PREPARED 'regress_manage_commit';  -- fails
ROLLBACK PREPARED 'regress_manage_rollback';  -- fails
RESET ROLE;

-- The manager needs no privileges on the affected table or preparing role.
GRANT pg_manage_prepared_xacts TO regress_prepare_manager;
SET ROLE regress_prepare_manager;
SELECT has_table_privilege('pxtest_manage', 'INSERT');
COMMIT PREPARED 'regress_manage_commit';
ROLLBACK PREPARED 'regress_manage_rollback';
RESET ROLE;

-- The privilege can be inherited indirectly.
SET ROLE regress_prepare_owner;
BEGIN;
INSERT INTO pxtest_manage VALUES (3);
PREPARE TRANSACTION 'regress_manage_commit';
BEGIN;
INSERT INTO pxtest_manage VALUES (4);
PREPARE TRANSACTION 'regress_manage_rollback';
RESET ROLE;
SET ROLE regress_prepare_indirect;
COMMIT PREPARED 'regress_manage_commit';
ROLLBACK PREPARED 'regress_manage_rollback';
RESET ROLE;

-- A non-inheriting member can explicitly SET ROLE to exercise the privilege.
SET ROLE regress_prepare_owner;
BEGIN;
INSERT INTO pxtest_manage VALUES (5);
PREPARE TRANSACTION 'regress_manage_commit';
BEGIN;
INSERT INTO pxtest_manage VALUES (6);
PREPARE TRANSACTION 'regress_manage_rollback';
RESET ROLE;
SET ROLE regress_prepare_noinherit;
SET ROLE pg_manage_prepared_xacts;
COMMIT PREPARED 'regress_manage_commit';
ROLLBACK PREPARED 'regress_manage_rollback';
RESET ROLE;

-- Revocation and regrant take effect even after the membership was cached.
SET ROLE regress_prepare_owner;
BEGIN;
INSERT INTO pxtest_manage VALUES (7);
PREPARE TRANSACTION 'regress_manage_commit';
BEGIN;
INSERT INTO pxtest_manage VALUES (8);
PREPARE TRANSACTION 'regress_manage_rollback';
RESET ROLE;
REVOKE pg_manage_prepared_xacts FROM regress_prepare_manager;
SET ROLE regress_prepare_manager;
COMMIT PREPARED 'regress_manage_commit';  -- fails after REVOKE
ROLLBACK PREPARED 'regress_manage_rollback';  -- fails after REVOKE
RESET ROLE;
GRANT pg_manage_prepared_xacts TO regress_prepare_manager;
SET ROLE regress_prepare_manager;
COMMIT PREPARED 'regress_manage_commit';
ROLLBACK PREPARED 'regress_manage_rollback';
RESET ROLE;

-- The management privilege also covers transactions prepared by superusers.
BEGIN;
INSERT INTO pxtest_manage VALUES (9);
PREPARE TRANSACTION 'regress_manage_commit';
BEGIN;
INSERT INTO pxtest_manage VALUES (10);
PREPARE TRANSACTION 'regress_manage_rollback';
SET ROLE regress_prepare_manager;
COMMIT PREPARED 'regress_manage_commit';
ROLLBACK PREPARED 'regress_manage_rollback';
RESET ROLE;

-- Superusers can still finish another user's transactions.
SET ROLE regress_prepare_owner;
BEGIN;
INSERT INTO pxtest_manage VALUES (11);
PREPARE TRANSACTION 'regress_manage_commit';
BEGIN;
INSERT INTO pxtest_manage VALUES (12);
PREPARE TRANSACTION 'regress_manage_rollback';
RESET ROLE;
COMMIT PREPARED 'regress_manage_commit';
ROLLBACK PREPARED 'regress_manage_rollback';

SELECT * FROM pxtest_manage ORDER BY a;
SELECT gid FROM pg_prepared_xacts WHERE gid LIKE 'regress_manage_%';
DROP TABLE pxtest_manage;
DROP ROLE regress_prepare_member;
DROP ROLE regress_prepare_owner;
DROP ROLE regress_prepare_indirect;
DROP ROLE regress_prepare_manager;
DROP ROLE regress_prepare_noinherit;
