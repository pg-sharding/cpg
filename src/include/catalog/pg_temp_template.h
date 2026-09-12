/*-------------------------------------------------------------------------
 *
 * pg_temp_template.h
 *	  definition of the "temporary table template" system catalog
 *	  (pg_temp_template)
 *
 * pg_temp_template stores definitions of temporary table templates.
 * Unlike pg_class rows for regular temp tables, template entries are
 * persistent: they are created once and reused across sessions. This
 * avoids catalog bloat caused by repeated CREATE/DROP of temporary
 * tables.
 *
 * Per-session storage (relfilenode, relpages, reltuples, etc.) is
 * tracked in backend memory, not in this catalog. See temp_template.c
 * for details.
 *
 * Portions Copyright (c) 1996-2026, PostgreSQL Global Development Group
 * Portions Copyright (c) 1994, Regents of the University of California
 *
 * src/include/catalog/pg_temp_template.h
 *
 * NOTES
 *	  The Catalog.pm module reads this file and derives schema
 *	  information.
 *
 *-------------------------------------------------------------------------
 */
#ifndef PG_TEMP_TEMPLATE_H
#define PG_TEMP_TEMPLATE_H

#include "catalog/genbki.h"
#include "catalog/pg_temp_template_d.h"	/* IWYU pragma: export */

/* ----------------
 *		pg_temp_template definition.  cpp turns this into
 *		typedef struct FormData_pg_temp_template
 * ----------------
 */
BEGIN_CATALOG_STRUCT

CATALOG(pg_temp_template,9820,TempTemplateRelationId) BKI_SCHEMA_MACRO
{
	/* OID of the template; also used as the relation OID */
	Oid			tmplid;

	/* template (table) name */
	NameData	tmplname;

	/* OID of namespace containing this template */
	Oid			tmplnamespace BKI_DEFAULT(pg_catalog) BKI_LOOKUP(pg_namespace);

	/* owner OID */
	Oid			tmplowner BKI_DEFAULT(POSTGRES) BKI_LOOKUP(pg_authid);

	/* relkind: 'r' for ordinary table, 'p' for partitioned table */
	char		tmplrelkind BKI_DEFAULT(r);

	/* number of user attributes */
	int16		tmplnatts BKI_DEFAULT(0);

	/* number of CHECK constraints */
	int16		tmplchecks BKI_DEFAULT(0);

	/* true if template is shared across databases */
	bool		tmplisshared BKI_DEFAULT(f);

	/* table AM OID */
	Oid			tmplam BKI_DEFAULT(heap) BKI_LOOKUP_OPT(pg_am);

	/* ON COMMIT action: 'n' = none, 'p' = preserve, 'd' = delete, 'D' = drop */
	char		tmploncommit BKI_DEFAULT(n);
} FormData_pg_temp_template;

END_CATALOG_STRUCT

/* ----------------
 *		Form_pg_temp_template corresponds to a pointer to a tuple with
 *		the format of pg_temp_template relation.
 * ----------------
 */
typedef FormData_pg_temp_template *Form_pg_temp_template;

DECLARE_UNIQUE_INDEX_PKEY(pg_temp_template_oid_index, 9821, TempTemplateOidIndexId, pg_temp_template, btree(tmplid oid_ops));
DECLARE_UNIQUE_INDEX(pg_temp_template_name_nsp_index, 9822, TempTemplateNameNspIndexId, pg_temp_template, btree(tmplname name_ops, tmplnamespace oid_ops));

MAKE_SYSCACHE(TEMPTEMPLATEOID, pg_temp_template_oid_index, 4);
MAKE_SYSCACHE(TEMPLATENAMENSP, pg_temp_template_name_nsp_index, 4);

#endif							/* PG_TEMP_TEMPLATE_H */
