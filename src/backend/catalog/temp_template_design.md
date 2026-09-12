# Temporary Template Tables: Design Document

## Problem

PostgreSQL stores temporary table definitions in shared catalogs (pg_class,
pg_attribute, pg_type, pg_index, pg_statistic). Every CREATE TEMP TABLE adds
rows to these catalogs; every DROP TEMP TABLE leaves dead tuples. High-frequency
CREATE/DROP cycles cause catalog bloat, forcing expensive autovacuum on shared
catalogs, degrading overall database performance.

## Design

### Overview

Split temporary table metadata into two layers:

1. **Template** (shared catalog, persistent, does not bloat)
   - Created once, reused across sessions
   - Stores: table name, schema, columns, types, index definitions
   - Lives in a new catalog table `pg_temp_template` + `pg_temp_template_attribute`

2. **Instance** (per-session, in-memory, ephemeral)
   - Created on first access in a session
   - Stores: relfilenode, relpages, reltuples, relfrozenxid, statistics
   - Deleted on session end or DROP TABLE
   - Uses local buffers (same as current temp tables)

### New catalog tables

#### pg_temp_template

Replaces pg_class rows for temp table definitions. Compact: only stores
identity and schema info, not storage or statistics.

```c
/* src/include/catalog/pg_temp_template.h */
CATALOG(pg_temp_template,XXXX,TempTemplateRelationId) BKI_ROWTYPE_OID(YYYY,TempTemplateRelation_TypeId)
{
    Oid         tmplid;          /* OID of the template (= rel OID) */
    NameData    tmplname;        /* table name */
    Oid         tmplnamespace;   /* schema OID */
    Oid         tmplowner;       /* owner OID */
    char        tmplrelkind;     /* 'r' = table, 'p' = partitioned, etc. */
    int16       tmplnatts;       /* number of user attributes */
    int16       tmplchecks;       /* # of CHECK constraints */
    bool        tmplisshared;     /* shared (across DBs) or not */
    bool        tmplhasoids;      /* has OIDs? */
    Oid         tmplam;          /* table AM OID */
    /* ON COMMIT action */
    char        tmploncommit;     /* 'n', 'p', 'd', 'D' */
} FormData_pg_temp_template;
```

#### pg_temp_template_attribute

Replaces pg_attribute rows for temp table definitions.

```c
CATALOG(pg_temp_template_attribute,ZZZZ)
{
    Oid         ttatmplid;       /* template OID */
    int16       ttaattnum;       /* attribute number */
    NameData    ttaattname;      /* attribute name */
    Oid         ttaatttypid;     /* type OID */
    int32       ttaattlen;       /* type length */
    int16       ttaatttypmod;    /* type modifier */
    bool        ttaattnotnull;   /* NOT NULL? */
    bool        ttaattisdropped; /* dropped? */
    char        ttaattidentity;  /* generated identity type */
    char        ttaattgenerated;/* generated stored/computed */
} FormData_pg_temp_template_attribute;
```

### Per-session instance tracking

In-memory hash table in each backend, keyed by template OID:

```c
typedef struct PgTempInstance
{
    Oid         template_oid;      /* pg_temp_template.tmplid */
    RelFileLocator rlocator;       /* local storage location */
    int64       relpages;          /* per-session relpages */
    float4      reltuples;         /* per-session reltuples */
    int64       relallvisible;     /* per-session relallvisible */
    int64       relallfrozen;      /* per-session relallfrozen */
    TransactionId relfrozenxid;    /* per-session relfrozenxid */
    MultiXactId relminmxid;        /* per-session relminmxid */
    SubTransactionId created_subid;
    SubTransactionId dropped_subid;
    /* Index state */
    List       *index_states;      /* list of PgTempIndexInstance */
} PgTempInstance;

typedef struct PgTempIndexInstance
{
    Oid         index_oid;         /* index OID (from template) */
    bool        indisvalid;        /* per-session validity */
    RelFileLocator rlocator;       /* local index storage */
} PgTempIndexInstance;
```

### SQL syntax

```sql
-- Create a template (persistent, shared across sessions)
CREATE TEMP TABLE TEMPLATE t1 (id int, value text);

-- Use it (creates instance on first access)
INSERT INTO t1 VALUES (1, 'hello');

-- Backward-compatible: creates template + instance
CREATE TEMP TABLE t2 (id int);

-- Drop instance only (template survives)
DROP TABLE t1;

-- Drop template (errors if instances in use)
DROP TEMP TABLE TEMPLATE t1;
```

### Compatibility view

To maintain backward compatibility with code that queries pg_class:

```sql
CREATE VIEW pg_class AS
    SELECT * FROM pg_class_actual
    UNION ALL
    SELECT tmplid AS oid, tmplname AS relname, ... FROM pg_temp_template
    WHERE /* only in current session's temp namespace */;
```

Or: make `pg_class` include template rows via a UNION ALL rewrite,
similar to how Dean Rasheed's GTT patch adds pg_temp_class entries.

### What changes in the backend

1. **DDL (CREATE TEMP TABLE)**:
   - With TEMPLATE keyword: create pg_temp_template + pg_temp_template_attribute rows
   - Without TEMPLATE: create template (if not exists) + trigger instance creation

2. **Relation open (relation_open / heap_open)**:
   - If rel OID is a template: look up or create instance in per-session hash
   - Instance provides relfilenode for storage access
   - Template provides tuple descriptor (from pg_temp_template_attribute)

3. **Storage (heapam)**:
   - No changes. Uses local buffers via relfilenode from instance.

4. **DDL (DROP TABLE)**:
   - DROP TABLE t1: drops instance (storage + in-memory state)
   - DROP TEMP TABLE TEMPLATE t1: drops template (error if instances active)

5. **DDL (ALTER TABLE on template)**:
   - ALTER TABLE TEMPLATE t1 ADD COLUMN: modifies pg_temp_template_attribute
   - Sends invalidation message to sessions using the template
   - Sessions rebuild instance on next access

6. **Transaction handling**:
   - Instance creation tracked via SubTransactionId (same as GTT patch)
   - Rollback: drop instance storage, remove from hash
   - Commit: instance persists until session end or DROP

7. **Statistics (ANALYZE)**:
   - Stored in per-session in-memory structure (not pg_statistic)
   - Planner uses per-session stats for temp tables

8. **Indexes**:
   - Index definitions stored in pg_temp_template (as part of template)
   - Index storage created per-session (in PgTempIndexInstance)
   - indisvalid can differ per session (index created by another session
     after this session already has data)

### What does NOT change

- Local buffer management
- WAL (temp tables don't write WAL)
- Crash recovery (temp files cleaned up on crash)
- Vacuum (vacuums local temp storage, not catalog)
- Autovacuum (can't vacuum temp tables, same as now)

### Open questions

1. Naming: TEMPLATE vs TYPE vs DEFINITION?
2. Should `CREATE TEMP TABLE` (without TEMPLATE) auto-create templates?
   - Yes: makes it transparent, solves bloat automatically
   - Risk: breaks `SELECT * FROM pg_class` patterns (templates appear)
3. How to handle ALTER TABLE on templates with active instances?
4. pg_dump: dump templates, not instances
5. Replicas: templates are in shared catalog (read-only OK), instances are local
6. Parallel query: instances in backend memory, same limitations as current temp tables
