/*-------------------------------------------------------------------------
 *
 * temp_template.c
 *	  Support routines for temporary table templates.
 *
 * Temporary table templates store table definitions (columns, types,
 * constraints) in a dedicated catalog (pg_temp_template) that does not
 * bloat pg_class. Per-session storage (relfilenode, statistics) is
 * tracked in backend memory.
 *
 * Portions Copyright (c) 1996-2026, PostgreSQL Global Development Group
 * Portions Copyright (c) 1994, Regents of the University of California
 *
 * src/backend/catalog/temp_template.c
 *
 *-------------------------------------------------------------------------
 */
#include "postgres.h"

#include "access/genam.h"
#include "access/heapam.h"
#include "access/multixact.h"
#include "access/reloptions.h"
#include "access/table.h"
#include "access/tableam.h"
#include "catalog/catalog.h"
#include "catalog/indexing.h"
#include "catalog/namespace.h"
#include "catalog/pg_temp_template.h"
#include "catalog/pg_temp_template_attribute.h"
#include "catalog/pg_type.h"
#include "commands/defrem.h"
#include "commands/tablecmds.h"
#include "common/relpath.h"
#include "miscadmin.h"
#include "nodes/makefuncs.h"
#include "nodes/parsenodes.h"
#include "storage/lmgr.h"
#include "utils/builtins.h"
#include "utils/fmgroids.h"
#include "utils/lsyscache.h"
#include "utils/rel.h"
#include "utils/syscache.h"

/*
 * Per-session instance hash table.
 *
 * Keyed by template OID, stores per-session storage info.
 */
static HTAB *temp_instance_hash = NULL;

typedef struct TempInstanceKey
{
	Oid			template_oid;
} TempInstanceKey;

typedef struct TempInstanceEntry
{
	TempInstanceKey key;

	/* Storage */
	RelFileLocator rlocator;
	ProcNumber	backend;

	/* Per-session statistics */
	int64		relpages;
	float4		reltuples;
	int64		relallvisible;
	int64		relallfrozen;
	TransactionId relfrozenxid;
	MultiXactId relminmxid;

	/* Transaction tracking */
	SubTransactionId created_subid;
	SubTransactionId dropped_subid;

	/* True if instance has been initialized (storage created) */
	bool		initialized;
} TempInstanceEntry;

/*
 * InitTempInstanceTable
 *		Initialize the per-session instance hash table (lazy).
 */
static void
InitTempInstanceTable(void)
{
	HASHCTL		ctl;

	if (temp_instance_hash != NULL)
		return;

	ctl.keysize = sizeof(TempInstanceKey);
	ctl.entrysize = sizeof(TempInstanceEntry);

	temp_instance_hash = hash_create("Temp template instance table",
									 64, &ctl, HASH_ELEM | HASH_BLOBS);
}

/*
 * CreateTempTemplate
 *		Create a new template entry in pg_temp_template.
 *
 * Returns the OID of the new template.
 */
Oid
CreateTempTemplate(const char *name, Oid namespaceId, Oid owner,
				   char relkind, int16 natts, Oid am,
				   char oncommit)
{
	Relation	pg_temp_template;
	TupleDesc	tupdesc;
	Datum		values[Natts_pg_temp_template];
	bool		nulls[Natts_pg_temp_template];
	Oid			tmplid;
	HeapTuple	tup;
	NameData	tmplname;

	/* Open pg_temp_template catalog */
	pg_temp_template = table_open(TempTemplateRelationId, RowExclusiveLock);
	tupdesc = RelationGetDescr(pg_temp_template);

	/* Generate OID */
	tmplid = GetNewOidWithIndex(pg_temp_template, TempTemplateOidIndexId,
								Anum_pg_temp_template_tmplid);

	/* Build tuple */
	MemSet(nulls, false, sizeof(nulls));
	namestrcpy(&tmplname, name);

	values[Anum_pg_temp_template_tmplid - 1] = ObjectIdGetDatum(tmplid);
	values[Anum_pg_temp_template_tmplname - 1] = NameGetDatum(&tmplname);
	values[Anum_pg_temp_template_tmplnamespace - 1] = ObjectIdGetDatum(namespaceId);
	values[Anum_pg_temp_template_tmplowner - 1] = ObjectIdGetDatum(owner);
	values[Anum_pg_temp_template_tmplrelkind - 1] = CharGetDatum(relkind);
	values[Anum_pg_temp_template_tmplnatts - 1] = Int16GetDatum(natts);
	values[Anum_pg_temp_template_tmplchecks - 1] = Int16GetDatum(0);
	values[Anum_pg_temp_template_tmplisshared - 1] = BoolGetDatum(false);
	values[Anum_pg_temp_template_tmplam - 1] = ObjectIdGetDatum(am);
	values[Anum_pg_temp_template_tmploncommit - 1] = CharGetDatum(oncommit);

	tup = heap_form_tuple(tupdesc, values, nulls);

	CatalogTupleInsert(pg_temp_template, tup);

	table_close(pg_temp_template, RowExclusiveLock);

	return tmplid;
}

/*
 * AddTempTemplateAttribute
 *		Add a column definition to pg_temp_template_attribute.
 */
void
AddTempTemplateAttribute(Oid template_oid, int16 attnum,
						 const char *attname, Oid atttypid,
						 int16 attlen, int32 atttypmod,
						 bool attnotnull, char attidentity,
						 char attgenerated)
{
	Relation	pg_tta;
	TupleDesc	tupdesc;
	Datum		values[Natts_pg_temp_template_attribute];
	bool		nulls[Natts_pg_temp_template_attribute];
	HeapTuple	tup;
	NameData	name;

	pg_tta = table_open(TempTemplateAttributeRelationId, RowExclusiveLock);
	tupdesc = RelationGetDescr(pg_tta);

	MemSet(nulls, false, sizeof(nulls));
	namestrcpy(&name, attname);

	values[Anum_pg_temp_template_attribute_ttatmplid - 1] = ObjectIdGetDatum(template_oid);
	values[Anum_pg_temp_template_attribute_ttaattnum - 1] = Int16GetDatum(attnum);
	values[Anum_pg_temp_template_attribute_ttaattname - 1] = NameGetDatum(&name);
	values[Anum_pg_temp_template_attribute_ttaatttypid - 1] = ObjectIdGetDatum(atttypid);
	values[Anum_pg_temp_template_attribute_ttaattlen - 1] = Int16GetDatum(attlen);
	values[Anum_pg_temp_template_attribute_ttaatttypmod - 1] = Int32GetDatum(atttypmod);
	values[Anum_pg_temp_template_attribute_ttaattnotnull - 1] = BoolGetDatum(attnotnull);
	values[Anum_pg_temp_template_attribute_ttaattisdropped - 1] = BoolGetDatum(false);
	values[Anum_pg_temp_template_attribute_ttaattidentity - 1] = CharGetDatum(attidentity);
	values[Anum_pg_temp_template_attribute_ttaattgenerated - 1] = CharGetDatum(attgenerated);

	tup = heap_form_tuple(tupdesc, values, nulls);
	CatalogTupleInsert(pg_tta, tup);

	table_close(pg_tta, RowExclusiveLock);
}

/*
 * GetTempTemplate
 *		Look up a template by OID. Returns NULL if not found.
 */
Form_pg_temp_template
GetTempTemplate(Oid tmplid)
{
	HeapTuple	tup;

	tup = SearchSysCache1(TEMPTEMPLATEOID, ObjectIdGetDatum(tmplid));
	if (!HeapTupleIsValid(tup))
		return NULL;

	/* Caller must ReleaseSysCache the result */
	return (Form_pg_temp_template) GETSTRUCT(tup);
}

/*
 * GetTempTemplateByName
 *		Look up a template by name and namespace.
 *		Returns OID of the template, or InvalidOid if not found.
 */
Oid
GetTempTemplateByName(const char *name, Oid namespaceId)
{
	HeapTuple	tup;

	tup = SearchSysCache2(TEMPLATENAMENSP,
						 PointerGetDatum(name),
						 ObjectIdGetDatum(namespaceId));
	if (!HeapTupleIsValid(tup))
		return InvalidOid;

	Oid			tmplid = ((Form_pg_temp_template) GETSTRUCT(tup))->tmplid;

	ReleaseSysCache(tup);
	return tmplid;
}

/*
 * DropTempTemplate
 *		Remove a template from pg_temp_template.
 *		Errors if any session has an active instance.
 */
void
DropTempTemplate(Oid tmplid)
{
	/* Check if any session has an active instance */
	InitTempInstanceTable();

	TempInstanceKey key;
	TempInstanceEntry *entry;
	bool		found;

	key.template_oid = tmplid;
	entry = hash_search(temp_instance_hash, &key, HASH_FIND, &found);

	if (found && entry->initialized)
		ereport(ERROR,
				(errcode(ERRCODE_OBJECT_NOT_IN_PREREQUISITE_STATE),
				 errmsg("cannot drop template table %u: still in use by this session",
						tmplid)));

	/* Delete from pg_temp_template */
	Relation	pg_temp_template = table_open(TempTemplateRelationId,
											  RowExclusiveLock);
	HeapTuple	tup = SearchSysCache1(TEMPTEMPLATEOID, ObjectIdGetDatum(tmplid));
	if (!HeapTupleIsValid(tup))
		elog(ERROR, "cache lookup failed for temp template %u", tmplid);

	CatalogTupleDelete(pg_temp_template, &tup->t_self);
	ReleaseSysCache(tup);
	table_close(pg_temp_template, RowExclusiveLock);

	/* Delete attributes */
	Relation	pg_tta = table_open(TempTemplateAttributeRelationId,
								   RowExclusiveLock);
	/* TODO: scan and delete all attributes with ttatmplid = tmplid */
	table_close(pg_tta, RowExclusiveLock);
}

/*
 * GetOrCreateTempInstance
 *		Find or create a per-session instance for the given template.
 *		Creates local storage if this is the first access in the session.
 */
TempInstanceEntry *
GetOrCreateTempInstance(Oid template_oid)
{
	InitTempInstanceTable();

	TempInstanceKey key;
	TempInstanceEntry *entry;
	bool		found;

	key.template_oid = template_oid;
	entry = hash_search(temp_instance_hash, &key, HASH_ENTER, &found);

	if (!found)
	{
		/* New instance: initialize */
		MemSet(entry, 0, sizeof(TempInstanceEntry));
		entry->key = key;
		entry->created_subid = GetCurrentSubTransactionId();
		entry->dropped_subid = InvalidSubTransactionId;
		entry->initialized = false;
	}

	if (!entry->initialized)
	{
		/* Create local storage */
		/* TODO: create relfilenode, local buffers, etc. */
		entry->backend = ProcNumberForTempRelations();
		entry->relpages = 0;
		entry->reltuples = -1;
		entry->relallvisible = 0;
		entry->relallfrozen = 0;
		entry->relfrozenxid = InvalidTransactionId;
		entry->relminmxid = FirstMultiXactId;
		entry->initialized = true;
	}

	return entry;
}

/*
 * DropTempInstance
 *		Remove the per-session instance (drop local storage).
 */
void
DropTempInstance(Oid template_oid)
{
	InitTempInstanceTable();

	TempInstanceKey key;
	TempInstanceEntry *entry;
	bool		found;

	key.template_oid = template_oid;
	entry = hash_search(temp_instance_hash, &key, HASH_FIND, &found);

	if (!found)
		return;

	if (entry->initialized)
	{
		/* TODO: delete local storage (relfilenode, buffers) */
	}

	hash_search(temp_instance_hash, &key, HASH_REMOVE, NULL);
}

/*
 * AtEOXactTempTemplates
 *		Cleanup at transaction end.
 */
void
AtEOXactTempTemplates(bool isCommit)
{
	if (temp_instance_hash == NULL)
		return;

	/* For now, just clean up on abort */
	if (!isCommit)
	{
		HASH_SEQ_STATUS status;
		TempInstanceEntry *entry;

		hash_seq_init(&status, temp_instance_hash);
		while ((entry = hash_seq_search(&status)) != NULL)
		{
			if (entry->created_subid != InvalidSubTransactionId)
			{
				/* Created in aborted transaction: drop */
				/* TODO: delete storage */
				TempInstanceKey key = entry->key;
				hash_search(temp_instance_hash, &key, HASH_REMOVE, NULL);
			}
		}
	}
}

/*
 * AutoCreateTempTableFromTemplate
 *		Create a regular TEMP TABLE from a template definition.
 *		Returns the OID of the newly created temp table.
 */
Oid
AutoCreateTempTableFromTemplate(Oid tmplid, const char *relname)
{
	HeapTuple	tup;
	Form_pg_temp_template tmpl;
	Relation	pg_tta;
	SysScanDesc scan;
	ScanKeyData key;
	List	   *tableElts = NIL;
	CreateStmt *cstmt;
	ObjectAddress addr;
	Oid			relid;

	/* Look up the template */
	tup = SearchSysCache1(TEMPTEMPLATEOID, ObjectIdGetDatum(tmplid));
	if (!HeapTupleIsValid(tup))
		elog(ERROR, "cache lookup failed for temp template %u", tmplid);
	tmpl = (Form_pg_temp_template) GETSTRUCT(tup);
	ReleaseSysCache(tup);

	/* Scan template attributes */
	pg_tta = table_open(TempTemplateAttributeRelationId, AccessShareLock);
	ScanKeyInit(&key, Anum_pg_temp_template_attribute_ttatmplid,
				BTEqualStrategyNumber, F_OIDEQ, ObjectIdGetDatum(tmplid));
	scan = systable_beginscan(pg_tta, TempTemplateAttributeIndexId, true,
							  NULL, 1, &key);

	while (HeapTupleIsValid(tup = systable_getnext(scan)))
	{
		Form_pg_temp_template_attribute attr = (Form_pg_temp_template_attribute) GETSTRUCT(tup);
		ColumnDef  *col;
		TypeName   *typename;

		typename = makeNode(TypeName);
		typename->typmods = NIL;
		typename->typeOid = attr->ttaatttypid;
		typename->setof = false;
		typename->pct_type = false;
		typename->location = -1;

		col = makeNode(ColumnDef);
		col->colname = pstrdup(NameStr(attr->ttaattname));
		col->typeName = typename;
		col->is_not_null = attr->ttaattnotnull;
		col->identity = attr->ttaattidentity;
		col->generated = attr->ttaattgenerated;
		col->location = -1;

		tableElts = lappend(tableElts, col);
	}
	systable_endscan(scan);
	table_close(pg_tta, AccessShareLock);

	/* Build CreateStmt for a TEMP table */
	cstmt = makeNode(CreateStmt);
	cstmt->relation = makeRangeVar(NULL, pstrdup(relname), -1);
	cstmt->relation->relpersistence = RELPERSISTENCE_TEMP;
	cstmt->tableElts = tableElts;
	cstmt->inhRelations = NIL;
	cstmt->partspec = NULL;
	cstmt->ofTypename = NULL;
	cstmt->constraints = NIL;
	cstmt->options = NIL;
	cstmt->oncommit = tmpl->tmploncommit;
	cstmt->tablespacename = NULL;
	cstmt->accessMethod = NULL;
	cstmt->if_not_exists = false;

	/* Create the temp table */
	addr = DefineRelation(cstmt, RELKIND_RELATION, InvalidOid, NULL, NULL);

	relid = addr.objectId;

	/* Create toast table if needed */
	CommandCounterIncrement();
	{
		Datum		toast_options;
		const char *const validnsps[] = HEAP_RELOPT_NAMESPACES;

		toast_options = transformRelOptions((Datum) 0, NIL, "toast",
											validnsps, true, false);
		(void) heap_reloptions(RELKIND_TOASTVALUE, toast_options, true);
		NewRelationCreateToastTable(relid, toast_options);
	}

	return relid;
}
