#include "/home/reshke/allfuzz/btree-typed-v8-firstattr-20261109-r1/source/V6/nbtsearch.c"
/* Diagnostic-only suffix for the complete frozen production TU.  Its static
 * search helper is called on live read-locked pages; this DSO is not used for
 * SQL timing or as a replacement access method. */
#include "access/genam.h"
#include "utils/array.h"
#include "utils/builtins.h"
PG_MODULE_MAGIC;
PG_FUNCTION_INFO_V1(firstattr_probe_v6);

Datum
firstattr_probe_v6(PG_FUNCTION_ARGS)
{
	Relation rel = index_open(PG_GETARG_OID(0), AccessShareLock);
	ArrayType *array = PG_GETARG_ARRAYTYPE_P(1);
	Datum *arguments;
	bool *nulls;
	int nargs;
	BTScanInsert key = _bt_mkscankey(rel, NULL);
	BlockNumber blocks = RelationGetNumberOfBlocks(rel);
	uint64 calls = 0, leaves = 0, internal = 0, checksum = 0;

	deconstruct_array(array, INT8OID, 8, true, 'd', &arguments, &nulls, &nargs);
	_bt_metaversion(rel, &key->heapkeyspace, &key->allequalimage);
	key->keysz = 1;
	key->scantid = NULL;
	key->anynullkeys = false;
	key->scankeys->sk_flags &= ~SK_ISNULL;
	key->scankeys->sk_argument = Int64GetDatum(0);
	if (!(key->keysz == 1 &&
		key->scankeys->sk_func.fn_oid == F_BTINT8CMP &&
		key->scankeys->sk_func.fn_addr == btint8cmp &&
		key->heapkeyspace && key->scantid == NULL &&
		!(key->scankeys->sk_flags & (SK_ISNULL | SK_BT_DESC)) &&
		key->scankeys->sk_attno == 1 &&
		IndexRelationGetNumberOfAttributes(rel) == 1 &&
		TupleDescAttr(RelationGetDescr(rel), 0)->atttypid == INT8OID))
		elog(ERROR, "oracle fixture is outside the production eligibility guard");
	for (BlockNumber block = 1; block < blocks; block++)
	{
		Buffer buffer = _bt_getbuf(rel, block, BT_READ);
		Page page = BufferGetPage(buffer);
		BTPageOpaque opaque = BTPageGetOpaque(page);
		bool leaf = P_ISLEAF(opaque);

		if (P_IGNORE(opaque))
		{
			_bt_relbuf(rel, buffer);
			continue;
		}
		if (leaf)
			leaves++;
		else
			internal++;
		for (int argument = 0; argument < nargs; argument++)
		{
			if (nulls[argument])
				elog(ERROR, "oracle arguments must be non-NULL");
			key->scankeys->sk_argument = arguments[argument];
			for (int flags = 0; flags < 4; flags++)
			{
				OffsetNumber first = P_FIRSTDATAKEY(opaque);
				OffsetNumber last = PageGetMaxOffsetNumber(page);
				OffsetNumber expected = first;
				OffsetNumber got;
				int cmpval;

				key->nextkey = (flags & 1) != 0;
				key->backward = (flags & 2) != 0;
				cmpval = key->nextkey ? 0 : 1;
				/* Independent linear walk, using the ordinary comparator. */
				if (last >= first)
				{
					if (!leaf)
						expected = OffsetNumberNext(expected);
					while (expected <= last &&
						   _bt_compare(rel, key, page, expected) >= cmpval)
						expected = OffsetNumberNext(expected);
					if (!leaf || key->backward)
						expected = OffsetNumberPrev(expected);
				}
				got = _bt_binsrch_int8_read(rel, key, buffer);
				if (got != expected)
					elog(ERROR, "offset mismatch block=%u leaf=%d arg=%d flags=%d got=%u expected=%u",
						 block, leaf, argument, flags, got, expected);
				calls++;
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
										 calls, leaves, internal, checksum)));
}
