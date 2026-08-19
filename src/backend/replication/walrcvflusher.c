/*-------------------------------------------------------------------------
 *
 * walrcvflusher.c
 *
 * The WAL receiver flusher makes streamed WAL durable.  The walreceiver
 * writes what it receives and publishes how far it got in
 * WalRcv->writtenUpto; this process fsyncs the segment files behind it and
 * publishes how far it got in WalRcv->flushedUpto, which is the position
 * everything that claims durability on a standby is measured against.
 *
 * Splitting the fsync out of the walreceiver keeps the receive path free of
 * disk latency: while a segment is being fsynced here, the walreceiver keeps
 * reading from the socket and writing, and the next fsync covers whatever
 * accumulated in the meantime.  Recovery is not held up either, because it
 * replays WAL as soon as it has been written and only waits for durability
 * when it is about to persist something derived from it; see
 * WalRcvWaitForFlush().
 *
 * The walreceiver wakes us after each batch of received WAL, and so does
 * anyone who starts waiting on WalRcv->flushCV, so the flush of received WAL
 * is never postponed past the point where somebody needs it.
 *
 * The flusher is started by the postmaster whenever the server might be in
 * recovery, and is terminated once recovery is over.  Like the walreceiver,
 * it is not essential for the walreceiver's own progress, so the walreceiver
 * still flushes on its own when closing a segment or when shutting down; that
 * also means the unflushed part of the stream is always contained in the
 * segment that is being written right now.
 *
 * Portions Copyright (c) 2010-2025, PostgreSQL Global Development Group
 *
 *
 * IDENTIFICATION
 *	  src/backend/replication/walrcvflusher.c
 *
 *-------------------------------------------------------------------------
 */
#include "postgres.h"

#include <unistd.h>

#include "access/xlog.h"
#include "access/xlog_internal.h"
#include "access/xlogrecovery.h"
#include "libpq/pqsignal.h"
#include "miscadmin.h"
#include "pgstat.h"
#include "postmaster/auxprocess.h"
#include "postmaster/interrupt.h"
#include "replication/walrcvflusher.h"
#include "replication/walreceiver.h"
#include "replication/walsender.h"
#include "storage/condition_variable.h"
#include "storage/fd.h"
#include "storage/ipc.h"
#include "storage/latch.h"
#include "storage/lwlock.h"
#include "storage/proc.h"
#include "storage/procsignal.h"
#include "utils/memutils.h"
#include "utils/wait_event.h"

/*
 * How long to sleep when there is nothing to flush.  The walreceiver and
 * anyone waiting for WAL to become durable wake us up, so this is only a
 * backstop, but it keeps the process from sleeping forever if a wakeup is
 * ever missed.
 */
#define WALRCVFLUSHER_NAPTIME	1000	/* milliseconds */

/* The segment we currently hold open for fsyncing, if any. */
static int	flushFile = -1;
static XLogSegNo flushSegNo = 0;
static TimeLineID flushTLI = 0;

static void WalRcvFlusherShutdown(int code, Datum arg);
static void WalRcvFlusherCloseSegment(void);
static void WalRcvFlusherFlush(void);


/* Main entry point for the WAL receiver flusher process */
void
WalRcvFlusherMain(const void *startup_data, size_t startup_data_len)
{
	WalRcvData *walrcv = WalRcv;
	sigjmp_buf	local_sigjmp_buf;
	MemoryContext context;

	Assert(startup_data_len == 0);

	MyBackendType = B_WAL_RCV_FLUSHER;
	AuxiliaryProcessMainCommon();

	ereport(DEBUG1,
			(errmsg_internal("WAL receiver flusher started")));

	/*
	 * Properly accept or ignore signals the postmaster might send us.
	 *
	 * We have no particular use for SIGINT, but seems reasonable to treat it
	 * like SIGTERM.
	 */
	pqsignal(SIGHUP, SignalHandlerForConfigReload);
	pqsignal(SIGINT, SignalHandlerForShutdownRequest);
	pqsignal(SIGTERM, SignalHandlerForShutdownRequest);
	/* SIGQUIT handler was already set up by InitPostmasterChild */
	pqsignal(SIGALRM, SIG_IGN);
	pqsignal(SIGPIPE, SIG_IGN);
	pqsignal(SIGUSR1, procsignal_sigusr1_handler);
	pqsignal(SIGUSR2, SIG_IGN); /* not used */

	/* Reset some signals that are accepted by postmaster but not here */
	pqsignal(SIGCHLD, SIG_DFL);

	/*
	 * Advertise ourselves, so that the walreceiver and anybody waiting for WAL
	 * to become durable can wake us up.
	 */
	on_shmem_exit(WalRcvFlusherShutdown, (Datum) 0);
	SpinLockAcquire(&walrcv->mutex);
	walrcv->flusherProcno = MyProcNumber;
	SpinLockRelease(&walrcv->mutex);

	/* Create and switch to a memory context that we can reset on error. */
	context = AllocSetContextCreate(TopMemoryContext,
									"WAL Receiver Flusher",
									ALLOCSET_DEFAULT_SIZES);
	MemoryContextSwitchTo(context);

	/*
	 * If an exception is encountered, processing resumes here.
	 *
	 * Anything that would leave WAL unflushed for good is a PANIC in the code
	 * we call, so an error here means something unexpected happened.  Clean up
	 * and retry; the walreceiver flushes on its own when it closes a segment,
	 * so a stretch of unflushed WAL is not lost, merely delayed.
	 */
	if (sigsetjmp(local_sigjmp_buf, 1) != 0)
	{
		/* Since not using PG_TRY, must reset error stack by hand */
		error_context_stack = NULL;

		/* Prevent interrupts while cleaning up */
		HOLD_INTERRUPTS();

		/* Report the error to the server log */
		EmitErrorReport();

		/* Release resources we might have acquired */
		LWLockReleaseAll();
		ConditionVariableCancelSleep();
		pgstat_report_wait_end();
		WalRcvFlusherCloseSegment();
		ReleaseAuxProcessResources(false);
		AtEOXact_Files(false);
		AtEOXact_HashTables(false);

		/*
		 * Now return to normal top-level context and clear ErrorContext for
		 * next time.
		 */
		MemoryContextSwitchTo(context);
		FlushErrorState();

		/* Flush any leaked data in the top-level context */
		MemoryContextReset(context);

		/* Now we can allow interrupts again */
		RESUME_INTERRUPTS();

		/*
		 * Sleep for a while before retrying, to avoid filling the log with
		 * repeated complaints about a condition that is unlikely to fix itself
		 * quickly.
		 */
		(void) WaitLatch(NULL,
						 WL_TIMEOUT | WL_EXIT_ON_PM_DEATH,
						 1000,
						 WAIT_EVENT_WAL_RCV_FLUSHER_MAIN);
	}

	/* We can now handle ereport(ERROR) */
	PG_exception_stack = &local_sigjmp_buf;

	/* Unblock signals (they were blocked when the postmaster forked us) */
	sigprocmask(SIG_SETMASK, &UnBlockSig, NULL);

	for (;;)
	{
		/*
		 * Reset the latch before looking at shared memory, so that a wakeup
		 * arriving while we are fsyncing is not lost: it will make the wait at
		 * the end of the loop return immediately.
		 */
		ResetLatch(MyLatch);

		/* Process any signals received recently */
		/* XXX: check for shutdown request */
		ProcessWalRcvInterrupts();
		
		/*
		 * Flush any WAL the walreceiver has written.  We are done for now if
		 * this leaves nothing behind; if the walreceiver wrote more while we
		 * were fsyncing, our latch is set and we'll come straight back.
		 */
		WalRcvFlusherFlush();

		(void) WaitLatch(MyLatch,
						 WL_LATCH_SET | WL_TIMEOUT | WL_EXIT_ON_PM_DEATH,
						 WALRCVFLUSHER_NAPTIME,
						 WAIT_EVENT_WAL_RCV_FLUSHER_MAIN);
	}
}

/*
 * Mark ourselves as not running in shared memory at exit.
 */
static void
WalRcvFlusherShutdown(int code, Datum arg)
{
	WalRcvData *walrcv = WalRcv;

	SpinLockAcquire(&walrcv->mutex);
	walrcv->flusherProcno = INVALID_PROC_NUMBER;
	SpinLockRelease(&walrcv->mutex);

	/*
	 * Anyone waiting for WAL to become durable has to recheck now that nobody
	 * is going to flush it on their behalf.  They give up if the walreceiver
	 * has stopped, and the walreceiver flushes what it wrote before it stops.
	 */
	ConditionVariableBroadcast(&walrcv->flushCV);
}

/*
 * Close the segment we hold open, if any.
 */
static void
WalRcvFlusherCloseSegment(void)
{
	if (flushFile < 0)
		return;

	if (close(flushFile) != 0)
	{
		char		xlogfname[MAXFNAMELEN];

		XLogFileName(xlogfname, flushTLI, flushSegNo, wal_segment_size);
		ereport(PANIC,
				(errcode_for_file_access(),
				 errmsg("could not close WAL segment %s: %m", xlogfname)));
	}

	flushFile = -1;
	flushSegNo = 0;
	flushTLI = 0;
}

/*
 * Make the WAL the walreceiver has written durable, and tell the world about
 * it.
 */
static void
WalRcvFlusherFlush(void)
{
	WalRcvData *walrcv = WalRcv;
	XLogRecPtr	written;
	XLogRecPtr	flushed;
	TimeLineID	tli;
	XLogSegNo	segno;
	bool		advanced = false;

	/*
	 * Nothing to do unless the walreceiver is streaming.  When it is not, it
	 * has already flushed whatever it wrote, and writtenUpto may refer to a
	 * stream that is gone.
	 */
	if (!WalRcvStreaming())
		return;

	written = GetWalRcvWrittenRecPtr(NULL, &tli);
	flushed = GetWalRcvFlushRecPtr(NULL, NULL);

	if (XLogRecPtrIsInvalid(written) || written <= flushed || tli == 0)
		return;

	/*
	 * The walreceiver flushes a segment before it moves on to the next one, so
	 * everything up to the start of the segment holding 'written' is durable
	 * already and this one fsync is all we need.
	 */
	XLByteToPrevSeg(written, segno, wal_segment_size);

	if (flushFile >= 0 && (flushSegNo != segno || flushTLI != tli))
		WalRcvFlusherCloseSegment();

	if (flushFile < 0)
	{
		flushFile = XLogFileOpen(segno, tli);
		flushSegNo = segno;
		flushTLI = tli;
	}

	issue_xlog_fsync(flushFile, segno, tli);

	/*
	 * Publish the new durable position, unless the stream we just fsynced is
	 * no longer the stream the walreceiver is on: a new stream resets
	 * writtenUpto, and starts over on its own timeline, so in that case what
	 * we have is not something to report progress about.
	 */
	SpinLockAcquire(&walrcv->mutex);
	if (walrcv->receivedTLI == tli &&
		pg_atomic_read_u64(&walrcv->writtenUpto) >= written &&
		walrcv->flushedUpto < written)
	{
		walrcv->latestChunkStart = walrcv->flushedUpto;
		walrcv->flushedUpto = written;
		advanced = true;
	}
	SpinLockRelease(&walrcv->mutex);

	if (!advanced)
		return;

	/* Release anyone held up waiting for this WAL to become durable */
	ConditionVariableBroadcast(&walrcv->flushCV);

	/*
	 * Let the startup process and any cascading standbys know that more WAL is
	 * durable, and ask the walreceiver to report the new flush position to the
	 * primary, which may have a transaction waiting for it.
	 */
	WakeupRecovery();
	if (AllowCascadeReplication())
		WalSndWakeup(true, false);
	WalRcvForceReply();
}

/*
 * Wake up the WAL receiver flusher, if it is running.
 */
void
WakeupWalRcvFlusher(void)
{
	WalRcvData *walrcv = WalRcv;
	ProcNumber	procno;

	if (walrcv == NULL)
		return;

	/* fetching the proc number is probably atomic, but don't rely on it */
	SpinLockAcquire(&walrcv->mutex);
	procno = walrcv->flusherProcno;
	SpinLockRelease(&walrcv->mutex);

	if (procno != INVALID_PROC_NUMBER)
		SetLatch(&GetPGProcByNumber(procno)->procLatch);
}
