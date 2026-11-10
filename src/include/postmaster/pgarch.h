/*-------------------------------------------------------------------------
 *
 * pgarch.h
 *	  Exports from postmaster/pgarch.c.
 *
 * Portions Copyright (c) 1996-2026, PostgreSQL Global Development Group
 * Portions Copyright (c) 1994, Regents of the University of California
 *
 * src/include/postmaster/pgarch.h
 *
 *-------------------------------------------------------------------------
 */
#ifndef _PGARCH_H
#define _PGARCH_H

#include "datatype/timestamp.h"
#include "port/atomics.h"
#include "storage/spin.h"

/* ----------
 * Archiver control info.
 *
 * We expect that archivable files within pg_wal will have names between
 * MIN_XFN_CHARS and MAX_XFN_CHARS in length, consisting only of characters
 * appearing in VALID_XFN_CHARS.  The status files in archive_status have
 * corresponding names with ".ready" or ".done" appended.
 * ----------
 */
#define MIN_XFN_CHARS	16
#define MAX_XFN_CHARS	40
#define VALID_XFN_CHARS "0123456789ABCDEF.history.backup.partial"

extern bool PgArchCanRestart(void);
pg_noreturn extern void PgArchiverMain(const void *startup_data, size_t startup_data_len);
extern void PgArchWakeup(void);
extern void PgArchForceDirScan(void);

/* Experimental, opt-in delegation of completed regular WAL segments. */
#define PGARCH_DELEGATE_MAX_FILES 100
#define PGARCH_DELEGATE_FILENAME_LEN 24

typedef struct PgArchDelegateBatch
{
	uint64		id;
	TimestampTz deadline;
	pid_t		owner;
	int			nfiles;
	int			nprocessed;
	bool		sent;
	bool		complete;
	char		files[PGARCH_DELEGATE_MAX_FILES][PGARCH_DELEGATE_FILENAME_LEN + 1];
} PgArchDelegateBatch;

extern PGDLLIMPORT int ArchiveDelegateMaxFiles;
extern PGDLLIMPORT int ArchiveDelegateMinBacklog;
extern PGDLLIMPORT int ArchiveDelegateTimeout;
extern PGDLLIMPORT bool ArchiveDelegateAccept;
extern PGDLLIMPORT bool ArchiveDelegationEnabled;

extern void PgArchDelegateDisconnect(pid_t owner);

/* Shared memory area for archiver process */
typedef struct PgArchData
{
	int			pgprocno;		/* proc number of archiver process */

	/* Protects archive reports and both delegation batches. */
	slock_t		lock;

	/* Last archived WAL segment file reported by the primary */
	char primary_last_archived[MAX_XFN_CHARS + 1];

	TimestampTz last_archival_report_timestamp;

	/*
	 * Forces a directory scan in pgarch_readyXlog().
	 */
	pg_atomic_uint32 force_dir_scan;

	/* Both batches are protected by lock. Zero id means no active batch. */
	uint64		next_delegate_id;
	PgArchDelegateBatch outgoing;
	PgArchDelegateBatch incoming;
} PgArchData;


extern PgArchData *PgArch;


#endif							/* _PGARCH_H */
