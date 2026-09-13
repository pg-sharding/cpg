/*-------------------------------------------------------------------------
 *
 * pg_temp_template_attribute.h
 *	  definition of the "temp template attribute" system catalog
 *	  (pg_temp_template_attribute)
 *
 * Stores column definitions for temporary table templates, analogous
 * to how pg_attribute stores column definitions for regular relations.
 * Kept separate from pg_attribute to avoid catalog bloat.
 *
 * Portions Copyright (c) 1996-2026, PostgreSQL Global Development Group
 * Portions Copyright (c) 1994, Regents of the University of California
 *
 * src/include/catalog/pg_temp_template_attribute.h
 *
 * NOTES
 *	  The Catalog.pm module reads this file and derives schema
 *	  information.
 *
 *-------------------------------------------------------------------------
 */
#ifndef PG_TEMP_TEMPLATE_ATTRIBUTE_H
#define PG_TEMP_TEMPLATE_ATTRIBUTE_H

#include "catalog/genbki.h"
#include "catalog/pg_temp_template_attribute_d.h"	/* IWYU pragma: export */

/* ----------------
 *		pg_temp_template_attribute definition.
 * ----------------
 */
BEGIN_CATALOG_STRUCT

CATALOG(pg_temp_template_attribute,9830,TempTemplateAttributeRelationId) BKI_SCHEMA_MACRO
{
	/* OID of the template this attribute belongs to */
	Oid			ttatmplid BKI_LOOKUP(pg_temp_template);

	/* attribute number (1-based for user columns) */
	int16		ttaattnum;

	/* attribute name */
	NameData	ttaattname;

	/* OID of data type */
	Oid			ttaatttypid BKI_LOOKUP_OPT(pg_type);

	/* type length (copy from pg_type.typlen) */
	int16		ttaattlen;

	/* type modifier */
	int32		ttaatttypmod BKI_DEFAULT(-1);

	/* NOT NULL constraint? */
	bool		ttaattnotnull BKI_DEFAULT(f);

	/* column dropped? */
	bool		ttaattisdropped BKI_DEFAULT(f);

	/* generated identity type: '\0' = none, 'a' = always, 'd' = by default */
	char		ttaattidentity BKI_DEFAULT('\0');

	/* generated column: '\0' = not generated, 's' = stored */
	char		ttaattgenerated BKI_DEFAULT('\0');
} FormData_pg_temp_template_attribute;

END_CATALOG_STRUCT

typedef FormData_pg_temp_template_attribute *Form_pg_temp_template_attribute;

DECLARE_UNIQUE_INDEX_PKEY(pg_temp_template_attribute_index, 9831, TempTemplateAttributeIndexId, pg_temp_template_attribute, btree(ttatmplid oid_ops, ttaattnum int2_ops));

MAKE_SYSCACHE(TEMPTEMPLATEATTR, pg_temp_template_attribute_index, 8);

#endif							/* PG_TEMP_TEMPLATE_ATTRIBUTE_H */
