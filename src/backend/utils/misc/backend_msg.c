/*-------------------------------------------------------------------------
 *
 * backend_msg.c
 *		Support for passing messages to backends being canceled or
 *		terminated.
 *
 * A backend that is about to signal another backend via
 * pg_cancel_backend() or pg_terminate_backend() may first stash a short
 * message in the target's slot, which the target backend then includes
 * in the error it reports to its client (see ProcessInterrupts()).
 *
 * There is one slot per backend, indexed by ProcNumber, so a message
 * can be stored without any locks on the target PGPROC.
 *
 * Portions Copyright (c) 1996-2026, PostgreSQL Global Development Group
 * Portions Copyright (c) 1994, Regents of the University of California
 *
 * src/backend/utils/misc/backend_msg.c
 *
 *-------------------------------------------------------------------------
 */
#include "postgres.h"

#include "mb/pg_wchar.h"
#include "miscadmin.h"
#include "storage/ipc.h"
#include "storage/proc.h"
#include "storage/spin.h"
#include "utils/backend_msg.h"


/*
 * One message slot per backend, indexed by ProcNumber.
 */
typedef struct BackendMsgSlot
{
	slock_t		lock;			/* protects the whole slot */
	int			pid;			/* backend's PID, 0 if unused */
	char		msg[BACKEND_MSG_MAX_LEN];	/* pending message, if any */
} BackendMsgSlot;

static BackendMsgSlot *BackendMsgSlots = NULL;

static void backend_msg_slot_clean(int code, Datum arg);


/*
 * BackendMsgShmemSize
 *		Report number of bytes needed for the message slots.
 */
Size
BackendMsgShmemSize(void)
{
	return mul_size(MaxBackends, sizeof(BackendMsgSlot));
}

/*
 * BackendMsgShmemInit
 *		Initialize (or attach to) the shared message slots.
 */
void
BackendMsgShmemInit(void)
{
	bool		found;

	BackendMsgSlots = (BackendMsgSlot *)
		ShmemInitStruct("BackendMsgSlots", BackendMsgShmemSize(), &found);

	if (!found)
	{
		/*
		 * Zero the whole array and initialize the spinlocks.  A zeroed
		 * slot is unused (pid == 0).
		 */
		MemSet(BackendMsgSlots, 0, BackendMsgShmemSize());
		for (int i = 0; i < MaxBackends; i++)
			SpinLockInit(&BackendMsgSlots[i].lock);
	}
}

/*
 * BackendMsgInit
 *		Initialize the message slot of the backend with the given proc
 *		number, and arrange for it to be cleaned up at exit.
 *
 * This must be called after the proc number is assigned during backend
 * startup, and before the backend can become visible to
 * pg_cancel_backend()/pg_terminate_backend().
 */
void
BackendMsgInit(int id)
{
	BackendMsgSlot *slot = &BackendMsgSlots[id];

	SpinLockAcquire(&slot->lock);

	/* the slot should have been reset by the previous owner */
	if (slot->pid != 0)
		elog(LOG, "process %d taking over backend message slot %d, but it's not empty",
			 MyProcPid, id);

	slot->pid = MyProcPid;
	slot->msg[0] = '\0';

	SpinLockRelease(&slot->lock);

	/* Set up to release the slot on process exit */
	on_shmem_exit(backend_msg_slot_clean, Int32GetDatum(0) /* not used */);
}

/*
 * backend_msg_slot_clean
 *		Release our message slot at backend shutdown.
 *
 * This function is called via on_shmem_exit() during backend shutdown.
 * It is registered after InitProcess() has registered its own cleanup
 * callbacks, so it runs before the proc number is released.
 */
static void
backend_msg_slot_clean(int code, Datum arg)
{
	BackendMsgSlot *slot = &BackendMsgSlots[MyProcNumber];

	SpinLockAcquire(&slot->lock);
	slot->pid = 0;
	slot->msg[0] = '\0';
	SpinLockRelease(&slot->lock);
}

/*
 * BackendMsgSet
 *		Store a message for the backend with the given proc number.
 *
 *		Returns the number of bytes actually stored, 0 for an empty or
 *		NULL message, or -1 if the target slot is not owned by a live
 *		backend.
 */
int
BackendMsgSet(ProcNumber procno, const char *msg)
{
	BackendMsgSlot *slot;
	int			len;

	if (msg == NULL || msg[0] == '\0')
		return 0;

	slot = &BackendMsgSlots[procno];

	SpinLockAcquire(&slot->lock);

	if (slot->pid == 0)
	{
		SpinLockRelease(&slot->lock);
		ereport(LOG,
				(errmsg("can't set message for missing backend, requested by %ld",
						(long) MyProcPid)));
		return -1;
	}

	len = pg_mbcliplen(msg, strlen(msg), sizeof(slot->msg) - 1);
	memcpy(slot->msg, msg, len);
	slot->msg[len] = '\0';

	SpinLockRelease(&slot->lock);

	return len;
}

/*
 * BackendMsgGet
 *		Copy our message into buf (at most max_len - 1 bytes plus a
 *		terminating '\0') and consume it.
 *
 *		Returns the number of bytes copied.
 */
int
BackendMsgGet(char *buf, int max_len)
{
	BackendMsgSlot *slot = &BackendMsgSlots[MyProcNumber];
	int			len;

	SpinLockAcquire(&slot->lock);

	len = strlen(slot->msg);
	if (len > max_len - 1)
		len = max_len - 1;
	memcpy(buf, slot->msg, len);
	buf[len] = '\0';

	/* the message is consumed */
	slot->msg[0] = '\0';

	SpinLockRelease(&slot->lock);

	return len;
}

/*
 * BackendMsgIsSet
 *		Have we got a pending message to include in an interrupt report?
 */
bool
BackendMsgIsSet(void)
{
	BackendMsgSlot *slot = &BackendMsgSlots[MyProcNumber];
	bool		is_set;

	SpinLockAcquire(&slot->lock);
	is_set = (slot->pid != 0 && slot->msg[0] != '\0');
	SpinLockRelease(&slot->lock);

	return is_set;
}
