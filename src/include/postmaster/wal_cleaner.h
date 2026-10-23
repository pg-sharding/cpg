/*-------------------------------------------------------------------------
 * wal_cleaner.h
 *		declaration for the WAL cleaner background worker
 *
 * Portions Copyright (c) 1996-2026, PostgreSQL Global Development Group
 * Portions Copyright (c) 1994, Regents of the University of California
 *
 * src/include/postmaster/wal_cleaner.h
 *-------------------------------------------------------------------------
 */
#ifndef WAL_CLEANER_H
#define WAL_CLEANER_H

/* GUC parameters */
extern PGDLLIMPORT bool wal_cleaner;
extern PGDLLIMPORT int wal_cleaner_interval;

extern void WalCleanerRegister(void);

extern pg_noreturn PGDLLEXPORT void WalCleanerMain(Datum main_arg);

#endif							/* WAL_CLEANER_H */
