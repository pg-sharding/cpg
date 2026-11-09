/* Untimed test shim appended to the ACTUAL complete normal nbtsearch.c TU.
 * Exported backend entry points are not invoked through this module. Only its
 * static binary-search helpers are called on read-locked live leaf pages. */
#include "access/genam.h"
#include "storage/bufmgr.h"
#include "catalog/pg_type_d.h"
#include "utils/array.h"
#include "utils/fmgroids.h"
#include "utils/fmgrprotos.h"
#include "utils/builtins.h"
PG_MODULE_MAGIC;
PG_FUNCTION_INFO_V1(@NAME@);
Datum
@NAME@(PG_FUNCTION_ARGS)
{
	Relation rel = index_open(PG_GETARG_OID(0), AccessShareLock);
	ArrayType *array = PG_GETARG_ARRAYTYPE_P(1);
	Datum *arguments;
	bool *nulls;
	int nargs;
	BTScanInsert key = _bt_mkscankey(rel, NULL);
	BlockNumber blocks = RelationGetNumberOfBlocks(rel);
	uint64 calls = 0, pages = 0, checksum = 0, eligible = 0;

	deconstruct_array(array, INT8OID, 8, true, 'd',
					  &arguments, &nulls, &nargs);
	key->keysz = 1;
	key->scantid = NULL;
	key->anynullkeys = false;
	key->scankeys->sk_flags &= ~SK_ISNULL;
	for (BlockNumber block = 1; block < blocks; block++)
	{
		Buffer buffer = _bt_getbuf(rel, block, BT_READ);
		Page page = BufferGetPage(buffer);
		BTPageOpaque opaque = BTPageGetOpaque(page);

		if (!P_ISLEAF(opaque) || P_IGNORE(opaque))
		{
			_bt_relbuf(rel, buffer);
			continue;
		}
		pages++;
		for (int argument = 0; argument < nargs; argument++)
		{
			if (nulls[argument])
				elog(ERROR, "probe input must be non-NULL");
			key->scankeys->sk_argument = arguments[argument];
			for (int flags = 0; flags < 4; flags++)
			{
				OffsetNumber first = P_FIRSTDATAKEY(opaque);
				OffsetNumber last = PageGetMaxOffsetNumber(page);
				OffsetNumber expected = first;
				OffsetNumber got;
				int cmpval;
				bool use_typed;

				key->nextkey = (flags & 1) != 0;
				key->backward = (flags & 2) != 0;
				cmpval = key->nextkey ? 0 : 1;
				/* Independent linear offset oracle using the original comparator. */
				if (last >= first)
				{
					while (expected <= last &&
						   _bt_compare(rel, key, page, expected) >= cmpval)
						expected = OffsetNumberNext(expected);
					if (key->backward)
						expected = OffsetNumberPrev(expected);
				}
				use_typed = @GUARD@;
				got = @CALL@;
				if (got != expected)
					elog(ERROR, "leaf offset mismatch block=%u arg=%d flags=%d got=%u expected=%u",
						 block, argument, flags, got, expected);
				calls++;
				eligible += use_typed;
				checksum += got;
			}
		}
		_bt_relbuf(rel, buffer);
	}
	pfree(key);
	pfree(arguments);
	pfree(nulls);
	index_close(rel, AccessShareLock);
	PG_RETURN_TEXT_P(cstring_to_text(psprintf(UINT64_FORMAT ":" UINT64_FORMAT ":" UINT64_FORMAT ":" UINT64_FORMAT,
											 calls, pages, eligible, checksum)));
}
