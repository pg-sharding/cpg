/*-------------------------------------------------------------------------
 *
 * parallel_backup.c
 *	  Server-side handlers for parallel base backup protocol.
 *
 * Implements START_BACKUP, SEND_FILE_LIST, SEND_FILE, and STOP_BACKUP
 * replication commands that together allow a client to perform a base
 * backup using multiple parallel walsender connections.
 *
 * The coordinator connection issues START_BACKUP, SEND_FILE_LIST, and
 * STOP_BACKUP. Worker connections each issue SEND_FILE for individual
 * files from the list returned by SEND_FILE_LIST.
 *
 * Portions Copyright (c) 2026, PostgreSQL Global Development Group
 *
 * src/backend/backup/parallel_backup.c
 *
 *-------------------------------------------------------------------------
 */
#include "postgres.h"

#include <dirent.h>
#include <sys/stat.h>

#include "access/xlog.h"
#include "access/xlogbackup.h"
#include "backup/basebackup.h"
#include "catalog/pg_type_d.h"
#include "common/file_utils.h"
#include "executor/executor.h"
#include "libpq/libpq.h"
#include "libpq/pqformat.h"
#include "miscadmin.h"
#include "nodes/replnodes.h"
#include "replication/walsender_private.h"
#include "storage/fd.h"
#include "tcop/dest.h"
#include "utils/builtins.h"
#include "utils/memutils.h"
#include "utils/pg_lsn.h"
#include "utils/timestamp.h"

/*
 * State that persists across START_BACKUP ... STOP_BACKUP on a single
 * walsender connection. Stored in a static variable since each walsender
 * is a separate process and the coordinator connection is the only one
 * that calls both START_BACKUP and STOP_BACKUP.
 */
static BackupState *parallel_backup_state = NULL;
static StringInfoData parallel_tablespace_map;
static bool parallel_backup_active = false;

/* Exclusion lists — mirrors basebackup.c excludeDirContents/excludeFiles */
static const char *const parallel_excludeDirContents[] =
{
	"pg_stat_tmp",
	"pg_replslot",
	"pg_dynshmem",
	"pg_notify",
	"pg_serial",
	"pg_snapshots",
	"pg_subtrans",
	NULL
};

static const char *const parallel_excludeFiles[] =
{
	"postgresql.auto.conf.tmp",
	"logmeta.json.tmp",
	"pg_internal.init",
	"backup_label",
	"tablespace_map",
	NULL
};

static void collect_file_list(const char *path, int basepathlen,
							  DestReceiver *dest, TupOutputState *tstate);
static bool is_excluded_dir(const char *name);
static bool is_excluded_file(const char *name);

static void
SendCopyOutResponse(void)
{
	StringInfoData buf;

	pq_beginmessage(&buf, PqMsg_CopyOutResponse);
	pq_sendbyte(&buf, 0);		/* overall format */
	pq_sendint16(&buf, 0);		/* natts */
	pq_endmessage(&buf);
}

static void
SendCopyDone(void)
{
	pq_putemptymessage(PqMsg_CopyDone);
}

/*
 * START_BACKUP [LABEL 'label']
 *
 * Returns a result set with one row: (backup_label text, start_lsn pg_lsn, start_tli int4)
 */
void
HandleStartBackup(StartBackupCmd *cmd)
{
	DestReceiver *dest;
	TupOutputState *tstate;
	TupleDesc	tupdesc;
	Datum		values[3];
	bool		nulls[3] = {false, false, false};
	char	   *backup_label;

	if (parallel_backup_active)
		ereport(ERROR,
				(errcode(ERRCODE_OBJECT_NOT_IN_PREREQUISITE_STATE),
				 errmsg("a parallel backup is already in progress")));

	WalSndSetState(WALSNDSTATE_BACKUP);

	/*
	 * Allocate backup state in TopMemoryContext so it survives across
	 * multiple replication commands (cmd_context is reset between commands).
	 */
	{
		MemoryContext oldctx = MemoryContextSwitchTo(TopMemoryContext);
		parallel_backup_state = palloc0(sizeof(BackupState));
		initStringInfo(&parallel_tablespace_map);
		MemoryContextSwitchTo(oldctx);
	}

	do_pg_backup_start(cmd->label, false, NULL,
					  parallel_backup_state, &parallel_tablespace_map);

	parallel_backup_active = true;

	backup_label = build_backup_content(parallel_backup_state, false);

	dest = CreateDestReceiver(DestRemoteSimple);

	tupdesc = CreateTemplateTupleDesc(3);
	TupleDescInitBuiltinEntry(tupdesc, (AttrNumber) 1, "backup_label", TEXTOID, -1, 0);
	TupleDescInitBuiltinEntry(tupdesc, (AttrNumber) 2, "start_lsn", TEXTOID, -1, 0);
	TupleDescInitBuiltinEntry(tupdesc, (AttrNumber) 3, "start_tli", INT4OID, -1, 0);
	TupleDescFinalize(tupdesc);

	tstate = begin_tup_output_tupdesc(dest, tupdesc, &TTSOpsVirtual);

	values[0] = CStringGetTextDatum(backup_label);
	values[1] = CStringGetTextDatum(psprintf("%X/%08X",
											 LSN_FORMAT_ARGS(parallel_backup_state->startpoint)));
	values[2] = Int32GetDatum(parallel_backup_state->starttli);
	do_tup_output(tstate, values, nulls);

	end_tup_output(tstate);

	pfree(backup_label);
}

/*
 * SEND_FILE_LIST
 *
 * Returns a result set: (path text, size int8, mode int4, is_link bool)
 */
void
HandleSendFileList(void)
{
	DestReceiver *dest;
	TupOutputState *tstate;
	TupleDesc	tupdesc;

	if (!parallel_backup_active)
		ereport(ERROR,
				(errcode(ERRCODE_OBJECT_NOT_IN_PREREQUISITE_STATE),
				 errmsg("START_BACKUP must be called first")));

	dest = CreateDestReceiver(DestRemoteSimple);

	tupdesc = CreateTemplateTupleDesc(4);
	TupleDescInitBuiltinEntry(tupdesc, (AttrNumber) 1, "path", TEXTOID, -1, 0);
	TupleDescInitBuiltinEntry(tupdesc, (AttrNumber) 2, "size", INT8OID, -1, 0);
	TupleDescInitBuiltinEntry(tupdesc, (AttrNumber) 3, "mode", INT4OID, -1, 0);
	TupleDescInitBuiltinEntry(tupdesc, (AttrNumber) 4, "is_link", INT4OID, -1, 0);
	TupleDescFinalize(tupdesc);

	tstate = begin_tup_output_tupdesc(dest, tupdesc, &TTSOpsVirtual);

	collect_file_list(".", 1, dest, tstate);

	end_tup_output(tstate);
}

/*
 * SEND_FILE 'path'
 *
 * Sends the contents of a single file as a COPY OUT data stream.
 * The path is relative to PGDATA, like "./base/12345/heap".
 */
void
HandleSendFile(SendFileCmd *cmd)
{
	char		pathbuf[MAXPGPATH];
	struct stat statbuf;
	int			fd;
	char		buffer[BLCKSZ * 8];
	int			nbytes;

	/* Prevent path traversal */
	if (strstr(cmd->path, "..") != NULL)
		ereport(ERROR,
				(errcode(ERRCODE_INVALID_PARAMETER_VALUE),
				 errmsg("invalid file path: %s", cmd->path)));

	/* Path from SEND_FILE_LIST is relative like "./base/12345" */
	if (cmd->path[0] == '.' && cmd->path[1] == '/')
		snprintf(pathbuf, sizeof(pathbuf), "%s/%s", DataDir, cmd->path + 2);
	else
		snprintf(pathbuf, sizeof(pathbuf), "%s/%s", DataDir, cmd->path);

	if (lstat(pathbuf, &statbuf) != 0)
		ereport(ERROR,
				(errcode_for_file_access(),
				 errmsg("could not stat file \"%s\": %m", cmd->path)));

	if (S_ISDIR(statbuf.st_mode) || S_ISLNK(statbuf.st_mode))
		ereport(ERROR,
				(errcode(ERRCODE_WRONG_OBJECT_TYPE),
				 errmsg("\"%s\" is not a regular file", cmd->path)));

	fd = BasicOpenFile(pathbuf, O_RDONLY | PG_BINARY);
	if (fd < 0)
		ereport(ERROR,
				(errcode_for_file_access(),
				 errmsg("could not open file \"%s\": %m", cmd->path)));

	/* Start COPY OUT */
	SendCopyOutResponse();

	/* Send file contents as CopyData messages */
	while ((nbytes = read(fd, buffer, sizeof(buffer))) > 0)
	{
		pq_putmessage(PqMsg_CopyData, buffer, nbytes);
	}

	if (nbytes < 0)
		ereport(ERROR,
				(errcode_for_file_access(),
				 errmsg("could not read file \"%s\": %m", cmd->path)));

	close(fd);

	/* End COPY OUT */
	SendCopyDone();
}

/*
 * STOP_BACKUP
 *
 * Ends the backup and returns a result set: (stop_lsn pg_lsn, stop_tli int4, backup_label text)
 */
void
HandleStopBackup(void)
{
	DestReceiver *dest;
	TupOutputState *tstate;
	TupleDesc	tupdesc;
	Datum		values[3];
	bool		nulls[3] = {false, false, false};
	char	   *backup_label;

	if (!parallel_backup_active)
		ereport(ERROR,
				(errcode(ERRCODE_OBJECT_NOT_IN_PREREQUISITE_STATE),
				 errmsg("START_BACKUP must be called first")));

	do_pg_backup_stop(parallel_backup_state, false);

	parallel_backup_active = false;

	backup_label = build_backup_content(parallel_backup_state, false);

	dest = CreateDestReceiver(DestRemoteSimple);

	tupdesc = CreateTemplateTupleDesc(3);
	TupleDescInitBuiltinEntry(tupdesc, (AttrNumber) 1, "stop_lsn", TEXTOID, -1, 0);
	TupleDescInitBuiltinEntry(tupdesc, (AttrNumber) 2, "stop_tli", INT4OID, -1, 0);
	TupleDescInitBuiltinEntry(tupdesc, (AttrNumber) 3, "backup_label", TEXTOID, -1, 0);
	TupleDescFinalize(tupdesc);

	tstate = begin_tup_output_tupdesc(dest, tupdesc, &TTSOpsVirtual);

	values[0] = CStringGetTextDatum(psprintf("%X/%08X",
											 LSN_FORMAT_ARGS(parallel_backup_state->stoppoint)));
	values[1] = Int32GetDatum(parallel_backup_state->stoptli);
	values[2] = CStringGetTextDatum(backup_label);
	do_tup_output(tstate, values, nulls);

	end_tup_output(tstate);

	pfree(backup_label);
	pfree(parallel_backup_state);
	parallel_backup_state = NULL;
}

/*
 * Recursively collect all files under 'path' that should be included
 * in the backup.  Each file is sent as a row via do_tup_output.
 */
static void
collect_file_list(const char *path, int basepathlen,
				  DestReceiver *dest, TupOutputState *tstate)
{
	DIR		   *dir;
	struct dirent *de;
	char		pathbuf[MAXPGPATH * 2];

	dir = AllocateDir(path);
	if (dir == NULL)
		return;

	while ((de = ReadDir(dir, path)) != NULL)
	{
		struct stat statbuf;
		Datum		values[4];
		bool		nulls[4] = {false, false, false, false};

		CHECK_FOR_INTERRUPTS();

		if (strcmp(de->d_name, ".") == 0 || strcmp(de->d_name, "..") == 0)
			continue;

		if (strncmp(de->d_name, PG_TEMP_FILE_PREFIX,
					strlen(PG_TEMP_FILE_PREFIX)) == 0)
			continue;

		if (strcmp(de->d_name, ".DS_Store") == 0)
			continue;

		if (is_excluded_file(de->d_name))
			continue;

		snprintf(pathbuf, sizeof(pathbuf), "%s/%s", path, de->d_name);

		if (lstat(pathbuf, &statbuf) != 0)
			continue;

		/* Send entry */
		values[0] = CStringGetTextDatum(pathbuf + 2); /* skip "./" prefix */
		values[1] = Int64GetDatum(statbuf.st_size);
		values[2] = Int32GetDatum(statbuf.st_mode);
		values[3] = Int32GetDatum(S_ISLNK(statbuf.st_mode) ? 1 : 0);
		do_tup_output(tstate, values, nulls);

		if (S_ISDIR(statbuf.st_mode) && !is_excluded_dir(de->d_name))
		{
			collect_file_list(pathbuf, basepathlen, dest, tstate);
		}
	}

	FreeDir(dir);
}

static bool
is_excluded_dir(const char *name)
{
	int			i;

	for (i = 0; parallel_excludeDirContents[i] != NULL; i++)
	{
		if (strcmp(name, parallel_excludeDirContents[i]) == 0)
			return true;
	}
	return false;
}

static bool
is_excluded_file(const char *name)
{
	int			i;

	for (i = 0; parallel_excludeFiles[i] != NULL; i++)
	{
		if (strcmp(name, parallel_excludeFiles[i]) == 0)
			return true;
	}
	return false;
}
