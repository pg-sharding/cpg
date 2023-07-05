
15: 

7dfdf3a55ed: mdb_replication role patch
f6a3406fed8: Disallow cancelation of syncronous commit V1
4289037edd2: Extend multixact SLRU
d6842b7f65c: Allow mdb_admin to create LEAKPROOF functions
146a82b3a75: mdb admin sets session replication role
68312eae50b: [MDB-16648]: Allow mdb admin to kill specific superuser queries
ab8f5243195: provide [mdb -postgresql] restict grant roles in YC[MDB-16990]
8ccf1aa7c51: Allow mdb admin to tranfers ownership on non-superuser objects regressioon tests for mdb admin functionality[MDB-16988]
bf4cad5ecdd: MDB-17910: check MDB reserved application name fix
64fed445a14: MDB-16955 : disallow to kill repl mon in cloud
afeb1eb4c2f:  Fix mdb_replication role
5852300fb1d: pg_replication_slot_advance fix
c52bd070b56: Fix compilation errors

0db90bbcbdd: Demonstrate and fix lock of all SQL queries by pg_stat_statements
530019f966d: MDB-21297: forbit usage of COPY TO PROGRAMM and COPY FROM PROGRAMM to non-superuser
8c860bf4d66: Reimplement mdb-admin, refactor mdb_admin check and usages. 

3a89cc36c74: Implement mdb-locales patch
dc7d503498b: Add mdb locales patch, restore COPY from/to files, enable regress.
96c30d707a7: Role mdb_superuser: feature and regress testsing
2d5f40ce3c9: Refactor optional setlocale, fix minor issues
41f04495a89: Update dependencies: bump libmdblocales, add mdb-locales
adc0b21d39f: Allow mdb_superuser to have power of pg_database_owner
ac90e1819fa: MDB-23247: startup param for auth passthrough under unpriviledged user
2bf6f042542: Add tap-test for mdb service role auth 👍👌😉
9750b4efc44: Use fadvise to prefetch WAL in xlogrecovery
25f12802528: Fix tests after rebasecontrib tests 💅️️💅️️💅️️ now works
746dd65f557: MDB-23247: debug ouput for testing purposes lowered to DEBUG5 elog level





16: 

/* misc */

/* on branch mdb-16 cherry-picked 'as is' */
f6a3406fed8 -> 1effb23478e: Disallow cancelation of syncronous commit V1
4289037edd2 -> b542d608604: Extend multixact SLRU



/* mdb - admin + mdb_replication */
7dfdf3a55ed: mdb_replication role patch


d6842b7f65c: Allow mdb_admin to create LEAKPROOF functions
146a82b3a75: mdb admin sets session replication role
68312eae50b: [MDB-16648]: Allow mdb admin to kill specific superuser queries
8ccf1aa7c51: Allow mdb admin to tranfers ownership on non-superuser objects regressioon tests for mdb admin functionality[MDB-16988]
8c860bf4d66: Reimplement mdb-admin, refactor mdb_admin check and usages. 

/* sqashed to  */
52435055d7b: Mdb-admin patch and regression tests
/*******/

/* as is */
ab8f5243195->3fecc85426e: provide [mdb -postgresql] restict grant roles in YC[MDB-16990]

/* pack of mdb patches */
bf4cad5ecdd: MDB-17910: check MDB reserved application name fix
64fed445a14: MDB-16955 : disallow to kill repl mon in cloud
afeb1eb4c2f:  Fix mdb_replication role
5852300fb1d: pg_replication_slot_advance fix
c52bd070b56: Fix compilation errors

/* squashed to  */
52ea09c2d90: Pack of MDB-related patches:
/*  */

0db90bbcbdd: Demonstrate and fix lock of all SQL queries by pg_stat_statements
530019f966d: MDB-21297: forbit usage of COPY TO PROGRAMM and COPY FROM PROGRAMM to non-superuser

3a89cc36c74: Implement mdb-locales patch
dc7d503498b: Add mdb locales patch, restore COPY from/to files, enable regress.
96c30d707a7: Role mdb_superuser: feature and regress testsing
2d5f40ce3c9: Refactor optional setlocale, fix minor issues
41f04495a89: Update dependencies: bump libmdblocales, add mdb-locales
adc0b21d39f: Allow mdb_superuser to have power of pg_database_owner
ac90e1819fa: MDB-23247: startup param for auth passthrough under unpriviledged user
2bf6f042542: Add tap-test for mdb service role auth 👍👌😉
9750b4efc44: Use fadvise to prefetch WAL in xlogrecovery
25f12802528: Fix tests after rebasecontrib tests 💅️️💅️️💅️️ now works
746dd65f557: MDB-23247: debug ouput for testing purposes lowered to DEBUG5 elog level

