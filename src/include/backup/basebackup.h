/*-------------------------------------------------------------------------
 *
 * basebackup.h
 *	  Exports from replication/basebackup.c.
 *
 * Portions Copyright (c) 2010-2025, PostgreSQL Global Development Group
 *
 * src/include/backup/basebackup.h
 *
 *-------------------------------------------------------------------------
 */
#ifndef _BASEBACKUP_H
#define _BASEBACKUP_H

#include "nodes/replnodes.h"

/*
 * Minimum and maximum values of MAX_RATE option in BASE_BACKUP command.
 */
#define MAX_RATE_LOWER	32
#define MAX_RATE_UPPER	1048576

/* A sensitive catalog rewrite permanently disables the redacted format. */
#define MDB_REDACTED_BACKUP_DISABLED_FILE "MDB_REDACTED_BACKUP_DISABLED"
#define MDB_REDACTED_BACKUP_DISABLE_WAL_MAGIC \
	"MDB redacted backup disabled, format 1"

/*
 * Information about a tablespace
 *
 * In some usages, "path" can be NULL to denote the PGDATA directory itself.
 */
typedef struct
{
	Oid			oid;			/* tablespace's OID */
	char	   *path;			/* full path to tablespace's directory */
	char	   *rpath;			/* relative path if it's within PGDATA, else
								 * NULL */
	int64		size;			/* total size as sent; -1 if not known */
} tablespaceinfo;

struct IncrementalBackupInfo;

extern void CreateMDBRedactedBackupDisabledFile(void);
extern void DisableMDBRedactedBackupForRelation(Oid relid);
extern bool IsMDBRedactedCatalogFile(bool is_global,
									 RelFileNumber relfilenumber);
extern void SendBaseBackup(BaseBackupCmd *cmd,
						   struct IncrementalBackupInfo *ib,
						   bool redact_sensitive_catalogs);

#endif							/* _BASEBACKUP_H */
