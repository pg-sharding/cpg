static inline int
baselineCompare(const ItemPointerData *a, const ItemPointerData *b)
{
	uint64		ia = (uint64) GinItemPointerGetBlockNumber(a) << 32 | GinItemPointerGetOffsetNumber(a);
	uint64		ib = (uint64) GinItemPointerGetBlockNumber(b) << 32 | GinItemPointerGetOffsetNumber(b);

	return pg_cmp_u64(ia, ib);
}
