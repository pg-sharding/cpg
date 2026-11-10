#include "postgres.h"
#include "access/gin_private.h"
#include "baseline-compare.inc"
#undef printf

static uint64 state = UINT64CONST(0xd8b403e75ac1296f);
static uint64
next_value(void)
{
	state ^= state << 13;
	state ^= state >> 7;
	state ^= state << 17;
	return state;
}

static pg_noinline bool
check_pair(const ItemPointerData *a, const ItemPointerData *b)
{
	uint64 expected = (uint64) GinItemPointerGetBlockNumber(a) << 32 |
		GinItemPointerGetOffsetNumber(a);

	return ginItemPointerKey(a) == expected &&
		ginCompareItemPointers(a, b) == baselineCompare(a, b) &&
		(ginItemPointerKey(a) > ginItemPointerKey(b)) ==
		(baselineCompare(a, b) > 0);
}

int
main(void)
{
	const BlockNumber blocks[] = {0,1,0xffff,0x10000,0x10001,0x7fffffff,
		0x80000000,0xfffffffe,0xffffffff,0x12345678,0x8000ffff,0xffff8000};
	const OffsetNumber offsets[] = {0,1,2,MaxOffsetNumber,0x7fff,0x8000,0xfffe,0xffff};
	ItemPointerData items[lengthof(blocks) * lengthof(offsets)];
	uint64 checked = 0;
	unsigned residues = 0;
	int n = 0;

	StaticAssertStmt(sizeof(ItemPointerData) == 6, "expected six-byte TIDs");
	for (int i = 0; i < (int) lengthof(blocks); i++)
		for (int j = 0; j < (int) lengthof(offsets); j++)
			ItemPointerSet(&items[n++], blocks[i], offsets[j]);
	for (int i = 0; i < n; i++)
	{
		residues |= 1U << ((uintptr_t) &items[i] % 4);
		for (int j = 0; j < n; j++)
		{
			if (!check_pair(&items[i], &items[j]))
				return 1;
			checked++;
		}
	}
	for (int i = 0; i < 1000000; i++)
	{
		ItemPointerSet(&items[i % n], (uint32) next_value(), (uint16) next_value());
		ItemPointerSet(&items[(i + 1) % n], (uint32) next_value(), (uint16) next_value());
		if (!check_pair(&items[i % n], &items[(i + 1) % n]))
			return 2;
		checked++;
	}
	if (residues != 5)
		return 3;
	printf("{\"cases\":%llu,\"sizeof_tid\":%zu,\"alignment_residues\":%u}\n",
		   (unsigned long long) checked, sizeof(ItemPointerData), residues);
	return 0;
}
