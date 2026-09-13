/*-------------------------------------------------------------------------
 *
 * temp_template.h
 *	  Public interface for temporary table templates.
 *
 * Portions Copyright (c) 1996-2026, PostgreSQL Global Development Group
 * Portions Copyright (c) 1994, Regents of the University of California
 *
 * src/include/catalog/temp_template.h
 *
 *-------------------------------------------------------------------------
 */
#ifndef TEMP_TEMPLATE_H
#define TEMP_TEMPLATE_H

#include "postgres.h"
#include "catalog/pg_temp_template.h"
#include "storage/relfilelocator.h"
#include "utils/relcache.h"

/* Opaque per-session instance */
typedef struct TempInstanceEntry TempInstanceEntry;

/* DDL: create/drop templates */
extern Oid	CreateTempTemplate(const char *name, Oid namespaceId,
							   Oid owner, char relkind, int16 natts,
							   Oid am, char oncommit);
extern void AddTempTemplateAttribute(Oid template_oid, int16 attnum,
									 const char *attname, Oid atttypid,
									 int16 attlen, int32 atttypmod,
									 bool attnotnull, char attidentity,
									 char attgenerated);
extern void DropTempTemplate(Oid tmplid);

/* Lookup */
extern Form_pg_temp_template GetTempTemplate(Oid tmplid);
extern Oid	GetTempTemplateByName(const char *name, Oid namespaceId);

/* Per-session instance management */
extern TempInstanceEntry *GetOrCreateTempInstance(Oid template_oid);
extern void DropTempInstance(Oid template_oid);

/* Transaction cleanup */
extern void AtEOXactTempTemplates(bool isCommit);

/* Auto-create a temp table from a template */
extern Oid	AutoCreateTempTableFromTemplate(Oid tmplid, const char *relname);

#endif							/* TEMP_TEMPLATE_H */
