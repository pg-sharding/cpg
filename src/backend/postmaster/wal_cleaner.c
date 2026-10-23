/*-------------------------------------------------------------------------
 * wal_cleaner.c
 *
 * The WAL cleaner background worker removes or recycles obsolete WAL
 * segments before the next checkpoint gets around to it.  The horizon is
 * computed by XLogRecycleObsoleteWAL() using exactly the same rules the
 * checkpointer applies at checkpoint completion, so it only frees WAL
 * that became removable between checkpoints (e.g. after wal_keep_size was
 * lowered or a replication slot was dropped) and never removes WAL that
 * crash recovery may need.
 *
 * Portions Copyright (c) 1996-2026, PostgreSQL Global Development Group
 * Portions Copyright (c) 1994, Regents of the University of California
 *
 * IDENTIFICATION
 *	  src/backend/postmaster/wal_cleaner.c
 *
 *-------------------------------------------------------------------------
 */
#include "postgres.h"

#include "access/xlog.h"
#include "miscadmin.h"
#include "postmaster/bgworker.h"
#include "postmaster/interrupt.h"
#include "postmaster/wal_cleaner.h"
#include "storage/ipc.h"
#include "storage/latch.h"
#include "utils/guc.h"
#include "utils/wait_event.h"

/* GUC variables */
bool		wal_cleaner = false;
int			wal_cleaner_interval = 10;

pg_noreturn PGDLLEXPORT void WalCleanerMain(Datum main_arg);

/*
 * Register the WAL cleaner background worker, if enabled.
 */
void
WalCleanerRegister(void)
{
	BackgroundWorker worker;

	if (!wal_cleaner)
		return;

	memset(&worker, 0, sizeof(worker));
	worker.bgw_flags = BGWORKER_SHMEM_ACCESS;
	worker.bgw_start_time = BgWorkerStart_RecoveryFinished;
	worker.bgw_restart_time = 10;
	snprintf(worker.bgw_name, BGW_MAXLEN, "wal_cleaner");
	snprintf(worker.bgw_type, BGW_MAXLEN, "wal_cleaner");
	snprintf(worker.bgw_library_name, BGW_MAXLEN, "postgres");
	snprintf(worker.bgw_function_name, BGW_MAXLEN, "WalCleanerMain");
	worker.bgw_main_arg = (Datum) 0;

	RegisterBackgroundWorker(&worker);
}

/*
 * Main loop of the WAL cleaner background worker.
 */
pg_noreturn PGDLLEXPORT void
WalCleanerMain(Datum main_arg)
{
	/* Establish signal handlers. */
	pqsignal(SIGTERM, SignalHandlerForShutdownRequest);
	pqsignal(SIGHUP, SignalHandlerForConfigReload);

	BackgroundWorkerUnblockSignals();

	while (true)
	{
		int			rc;

		CHECK_FOR_INTERRUPTS();

		if (ShutdownRequestPending)
			proc_exit(0);

		if (ConfigReloadPending)
		{
			ConfigReloadPending = false;
			ProcessConfigFile(PGC_SIGHUP);
		}

		XLogRecycleObsoleteWAL();

		rc = WaitLatch(MyLatch,
					   WL_LATCH_SET | WL_TIMEOUT | WL_EXIT_ON_PM_DEATH,
					   wal_cleaner_interval * 1000L,
					   WAIT_EVENT_WAL_CLEANER_MAIN);

		if (rc & WL_LATCH_SET)
			ResetLatch(MyLatch);
	}
}
