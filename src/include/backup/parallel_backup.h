/*-------------------------------------------------------------------------
 *
 * parallel_backup.h
 *	  Server-side handlers for parallel base backup protocol.
 *
 * The parallel base backup protocol splits a base backup into four
 * separate replication commands:
 *
 *  START_BACKUP [LABEL 'label']   - begins the backup (checkpoint, backup_label)
 *  SEND_FILE_LIST                - returns a result set of files to back up
 *  SEND_FILE 'path'              - sends contents of a single file via COPY OUT
 *  STOP_BACKUP                   - ends the backup, returns manifest
 *
 * This allows a client (pg_basebackup --jobs=N) to open multiple walsender
 * connections and transfer files in parallel.
 *
 * Portions Copyright (c) 2026, PostgreSQL Global Development Group
 *
 * src/include/backup/parallel_backup.h
 *
 *-------------------------------------------------------------------------
 */
#ifndef PARALLEL_BACKUP_H
#define PARALLEL_BACKUP_H

#include "nodes/replnodes.h"

extern void HandleStartBackup(StartBackupCmd *cmd);
extern void HandleSendFileList(void);
extern void HandleSendFile(SendFileCmd *cmd);
extern void HandleStopBackup(void);

#endif							/* PARALLEL_BACKUP_H */
