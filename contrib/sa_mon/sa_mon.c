/*-------------------------------------------------------------------------
 *
 * sa_mon.c
 *	  Shared archive monitoring.
 *
 * Exposes the last WAL segment archived by the primary, as reported to this
 * server through the replication protocol and stored in the archiver's
 * shared memory (PgArchData.primary_last_archived).
 *
 * Copyright (c) 2025, PostgreSQL Global Development Group
 *
 * IDENTIFICATION
 *	  contrib/sa_mon/sa_mon.c
 *
 *-------------------------------------------------------------------------
 */
#include "postgres.h"

#include "fmgr.h"
#include "postmaster/pgarch.h"
#include "storage/spin.h"
#include "utils/builtins.h"

PG_MODULE_MAGIC_EXT(
					.name = "sa_mon",
					.version = PG_VERSION
);

PG_FUNCTION_INFO_V1(mdb_get_sa_info);

/*
 * mdb_get_sa_info
 *
 * Returns the name of the last WAL segment archived by the primary as
 * reported to this standby, or NULL if nothing has been reported yet.
 */
Datum
mdb_get_sa_info(PG_FUNCTION_ARGS)
{
	char		last_archived[MAX_XFN_CHARS + 1];

	if (PgArch == NULL)
		PG_RETURN_NULL();

	SpinLockAcquire(&PgArch->lock);
	memcpy(last_archived, PgArch->primary_last_archived, sizeof(last_archived));
	SpinLockRelease(&PgArch->lock);

	/* Be paranoid about the shared memory contents. */
	last_archived[MAX_XFN_CHARS] = '\0';

	if (last_archived[0] == '\0')
		PG_RETURN_NULL();

	PG_RETURN_TEXT_P(cstring_to_text(last_archived));
}
