/*-------------------------------------------------------------------------
 *
 * syncrepwaker.c
 *    Release synchronous replication waiters outside the WAL sender.
 *
 * WAL senders publish confirmed write/flush/apply positions under SyncRepLock
 * and set our latch when queued backends can be released.  This lets the
 * senders return to streaming while we traverse the queues and wake backends.
 * Multiple replies can be handled in a single pass over the queues.
 *
 * The postmaster starts this auxiliary process during normal operation.  An
 * unexpected failure is treated as a crash, since we modify shared queues.
 * On a clean exit we unregister and drain confirmed waiters; WAL senders
 * release waiters directly until a replacement has registered.
 *
 * Portions Copyright (c) 2026, PostgreSQL Global Development Group
 *
 * IDENTIFICATION
 *    src/backend/replication/syncrepwaker.c
 *
 *-------------------------------------------------------------------------
 */
#include "postgres.h"

#include <unistd.h>

#include "libpq/pqsignal.h"
#include "miscadmin.h"
#include "postmaster/auxprocess.h"
#include "postmaster/interrupt.h"
#include "replication/syncrep.h"
#include "replication/walsender_private.h"
#include "storage/ipc.h"
#include "storage/latch.h"
#include "storage/lwlock.h"
#include "storage/proc.h"
#include "storage/procsignal.h"
#include "utils/wait_event.h"

/* GUC parameter */
bool		SyncRepWaker = true;
int			SyncRepWakerDirectLimit = 0;

static void SyncRepWakerShutdown(int code, Datum arg);

void
SyncRepWakerMain(const void *startup_data, size_t startup_data_len)
{
	Assert(startup_data_len == 0);

	MyBackendType = B_SYNC_REP_WAKER;
	AuxiliaryProcessMainCommon();

	pqsignal(SIGHUP, SignalHandlerForConfigReload);
	pqsignal(SIGINT, SignalHandlerForShutdownRequest);
	pqsignal(SIGTERM, SignalHandlerForShutdownRequest);
	/* SIGQUIT handler was already set up by InitPostmasterChild. */
	pqsignal(SIGALRM, SIG_IGN);
	pqsignal(SIGPIPE, SIG_IGN);
	pqsignal(SIGUSR1, procsignal_sigusr1_handler);
	pqsignal(SIGUSR2, SIG_IGN);
	pqsignal(SIGCHLD, SIG_DFL);

	on_shmem_exit(SyncRepWakerShutdown, 0);
	LWLockAcquire(SyncRepLock, LW_EXCLUSIVE);
	Assert(WalSndCtl->syncRepWakerProcno == INVALID_PROC_NUMBER);
	WalSndCtl->syncRepWakerProcno = MyProcNumber;
	LWLockRelease(SyncRepLock);

	sigprocmask(SIG_SETMASK, &UnBlockSig, NULL);

	for (;;)
	{
		/* Reset before inspecting the queues, so no notification is lost. */
		ResetLatch(MyLatch);
		ProcessMainLoopInterrupts();
		SyncRepWakePendingWaiters();

		(void) WaitLatch(MyLatch,
						 WL_LATCH_SET | WL_TIMEOUT | WL_EXIT_ON_PM_DEATH,
						 1000L,
						 WAIT_EVENT_SYNC_REP_WAKER_MAIN);
	}
}

static void
SyncRepWakerShutdown(int code, Datum arg)
{
	/* Interlock with senders handing off responsibility for queued waiters. */
	LWLockAcquire(SyncRepLock, LW_EXCLUSIVE);
	WalSndCtl->syncRepWakerProcno = INVALID_PROC_NUMBER;
	LWLockRelease(SyncRepLock);

	/* A sender may have published a position immediately before our exit. */
	SyncRepWakePendingWaiters();
}
