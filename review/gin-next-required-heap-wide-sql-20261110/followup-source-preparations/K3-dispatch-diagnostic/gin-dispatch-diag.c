/* Untimed actual-AM front door for a separately instrumented K3 backend. */
#include "postgres.h"
#include "fmgr.h"
#include "access/genam.h"
#include "access/skey.h"
#include "catalog/pg_am_d.h"
#include "catalog/pg_type_d.h"
#include "lib/stringinfo.h"
#include "miscadmin.h"
#include "nodes/tidbitmap.h"
#include "storage/lockdefs.h"
#include "utils/builtins.h"
#include "utils/fmgroids.h"
#include "utils/jsonb.h"
#include "utils/rel.h"
#include "utils/snapmgr.h"

PG_MODULE_MAGIC;
PG_FUNCTION_INFO_V1(gin_dispatch_diag);
PG_FUNCTION_INFO_V1(gin_dispatch_diag_begin);
PG_FUNCTION_INFO_V1(gin_dispatch_diag_finish);

extern void gin_k3_diag_begin(void);
extern void gin_k3_diag_end(void);
extern char *gin_k3_diag_report(void);

Datum
gin_dispatch_diag_begin(PG_FUNCTION_ARGS)
{
	gin_k3_diag_begin();
	PG_RETURN_VOID();
}

Datum
gin_dispatch_diag_finish(PG_FUNCTION_ARGS)
{
	char *report;

	gin_k3_diag_end();
	report = gin_k3_diag_report();
	PG_RETURN_TEXT_P(cstring_to_text(report));
}

Datum
gin_dispatch_diag(PG_FUNCTION_ARGS)
{
	Oid indexoid = PG_GETARG_OID(0);
	Datum query = PG_GETARG_DATUM(1);
	int32 loops = PG_GETARG_INT32(2);
	Relation index;
	IndexScanDesc scan;
	ScanKeyData key;
	int64 total = 0;
	StringInfoData out;
	char *report;

	if (loops < 1 || loops > 3)
		elog(ERROR, "diagnostic loop count out of range");
	index = index_open(indexoid, AccessShareLock);
	if (index->rd_rel->relam != GIN_AM_OID)
		elog(ERROR, "expected GIN index");
	ScanKeyInit(&key, 1, 1, F_TS_MATCH_VQ, query);
	key.sk_subtype = TSQUERYOID;
	gin_k3_diag_begin();
	PG_TRY();
	{
		scan = index_beginscan_bitmap(index, GetActiveSnapshot(), NULL, 1);
		for (int i = 0; i < loops; i++)
		{
			TIDBitmap *bitmap = tbm_create(64 * 1024 * 1024, NULL);

			CHECK_FOR_INTERRUPTS();
			index_rescan(scan, &key, 1, NULL, 0);
			total += index_getbitmap(scan, bitmap);
			tbm_free(bitmap);
		}
		index_endscan(scan);
		report = gin_k3_diag_report();
		gin_k3_diag_end();
	}
	PG_CATCH();
	{
		gin_k3_diag_end();
		PG_RE_THROW();
	}
	PG_END_TRY();
	index_close(index, AccessShareLock);
	initStringInfo(&out);
	appendStringInfo(&out, "{\"loops\":%d,\"total_tids\":" INT64_FORMAT ",\"probe\":%s}", loops, total, report);
	PG_RETURN_DATUM(DirectFunctionCall1(jsonb_in, CStringGetDatum(out.data)));
}
