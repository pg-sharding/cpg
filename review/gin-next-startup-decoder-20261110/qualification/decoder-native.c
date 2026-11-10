/* Ordinary valid-input checks and an allocation-inclusive native decoder bench. */
#include "postgres.h"
#include "fmgr.h"
#include "access/gin_private.h"
#include "lib/stringinfo.h"
#include "miscadmin.h"
#include "utils/builtins.h"
#include <time.h>

PG_MODULE_MAGIC;
PG_FUNCTION_INFO_V1(gin_decoder_oracle);
PG_FUNCTION_INFO_V1(gin_decoder_bench);

typedef struct DecodeCase
{
	const char *name;
	int nitems;
	int blockshift;
	int segment_items;
	bool first_singleton;
} DecodeCase;

/* Every ItemPointer is a valid normal block/offset pair; no malformed inputs. */
static const DecodeCase cases[] = {
	{"one", 1, -1, 1, false},
	{"tail1", 2, -1, 8, false},
	{"tail2", 3, -1, 8, false},
	{"tail3", 4, -1, 8, false},
	{"batch4", 5, -1, 8, false},
	{"batch5", 6, -1, 8, false},
	{"batch8", 9, -1, 16, false},
	{"dense128", 128, -1, 128, false},
	{"dense4096", 4096, -1, 4096, false},
	{"dense_multi", 4096, -1, 127, false},
	{"first_singleton_grow", 4096, -1, 511, true},
	{"singletons", 64, -1, 1, false},
	{"delta2", 128, 0, 128, false},
	{"delta3", 128, 7, 128, false},
	{"delta4", 128, 14, 128, false},
	{"delta5", 128, 21, 128, false},
	{"delta6", 128, 24, 128, false},
	{"delta7", 2, 31, 2, false}
};

static ItemPointerData *
make_items(const DecodeCase *c)
{
	ItemPointerData *items = palloc_array(ItemPointerData, c->nitems);

	for (int i = 0; i < c->nitems; i++)
	{
		BlockNumber block;
		OffsetNumber offset;

		if (c->blockshift < 0)
		{
			block = (BlockNumber) (i / 128);
			offset = (OffsetNumber) (1 + i % 128);
		}
		else
		{
			block = (BlockNumber) (((uint64) i) << c->blockshift);
			offset = 1;
		}
		ItemPointerSet(&items[i], block, offset);
	}
	return items;
}

static GinPostingList *
compress_items(const DecodeCase *c, const ItemPointerData *items, int *length,
			   int *nsegments)
{
	StringInfoData encoded;
	int pos = 0;

	initStringInfo(&encoded);
	*nsegments = 0;
	while (pos < c->nitems)
	{
		int count = Min(c->segment_items, c->nitems - pos);
		int written;
		GinPostingList *segment;

		if (pos == 0 && c->first_singleton)
			count = 1;
		segment = ginCompressPostingList(items + pos, count, 8192, &written);
		if (written != count)
			elog(ERROR, "ordinary decode fixture exceeds segment size");
		appendBinaryStringInfo(&encoded, (const char *) segment,
							   SizeOfGinPostingList(segment));
		pfree(segment);
		pos += count;
		(*nsegments)++;
	}
	*length = encoded.len;
	return (GinPostingList *) encoded.data;
}

static uint64
verify_items(ItemPointer got, int count, const ItemPointerData *expected, int n)
{
	uint64 checksum = UINT64CONST(1469598103934665603);

	if (count != n)
		elog(ERROR, "decoder count %d differs from independent fixture %d", count, n);
	for (int i = 0; i < n; i++)
	{
		if (!ItemPointerEquals(&got[i], &expected[i]))
			elog(ERROR, "decoder differs from generated TID at item %d", i);
		if (i > 0 && ginCompareItemPointers(&got[i - 1], &got[i]) >= 0)
			elog(ERROR, "decoder output is not strictly ordered");
		checksum ^= ItemPointerGetBlockNumber(&got[i]);
		checksum *= UINT64CONST(1099511628211);
		checksum ^= ItemPointerGetOffsetNumber(&got[i]);
		checksum *= UINT64CONST(1099511628211);
	}
	return checksum;
}

Datum
gin_decoder_oracle(PG_FUNCTION_ARGS)
{
	StringInfoData report;
	int total = 0;

	initStringInfo(&report);
	appendStringInfoString(&report, "{\"status\":\"PASS_VALID_DECODER\",\"timing_samples\":0,\"cases\":[");
	for (int i = 0; i < lengthof(cases); i++)
	{
		const DecodeCase *c = &cases[i];
		ItemPointerData *expected = make_items(c);
		int length, segments, decoded;
		GinPostingList *encoded = compress_items(c, expected, &length, &segments);
		ItemPointer result = ginPostingListDecodeAllSegments(encoded, length, &decoded);
		uint64 checksum = verify_items(result, decoded, expected, c->nitems);

		appendStringInfo(&report, "%s{\"name\":\"%s\",\"items\":%d,\"bytes\":%d,\"segments\":%d,\"checksum\":\"" UINT64_FORMAT "\"}",
						 i ? "," : "", c->name, decoded, length, segments, checksum);
		total += decoded;
		pfree(result);
		pfree(encoded);
		pfree(expected);
		CHECK_FOR_INTERRUPTS();
	}
	appendStringInfo(&report, "],\"checked_items\":%d}", total);
	PG_RETURN_TEXT_P(cstring_to_text(report.data));
}

static double
cpu_ms(void)
{
	struct timespec value;

	if (clock_gettime(CLOCK_PROCESS_CPUTIME_ID, &value) != 0)
		elog(ERROR, "could not read own process CPU clock: %m");
	return value.tv_sec * 1000.0 + value.tv_nsec / 1000000.0;
}

/* Never called by the build/correctness stage. Preparation and oracle are untimed. */
Datum
gin_decoder_bench(PG_FUNCTION_ARGS)
{
	char *name = text_to_cstring(PG_GETARG_TEXT_PP(0));
	int loops = PG_GETARG_INT32(1);
	const DecodeCase *c = NULL;
	ItemPointerData *expected;
	GinPostingList *encoded;
	ItemPointer result;
	int length, segments, decoded;
	uint64 checksum, consumed = 0;
	double begin, elapsed;
	StringInfoData report;

	if (loops < 1 || loops > 1000000)
		elog(ERROR, "ordinary decoder benchmark loops out of range");
	for (int i = 0; i < lengthof(cases); i++)
		if (strcmp(name, cases[i].name) == 0)
			c = &cases[i];
	if (!c)
		elog(ERROR, "unknown ordinary decoder case");
	expected = make_items(c);
	encoded = compress_items(c, expected, &length, &segments);
	result = ginPostingListDecodeAllSegments(encoded, length, &decoded);
	checksum = verify_items(result, decoded, expected, c->nitems);
	pfree(result);
	begin = cpu_ms();
	for (int i = 0; i < loops; i++)
	{
		result = ginPostingListDecodeAllSegments(encoded, length, &decoded);
		consumed += decoded + ItemPointerGetBlockNumber(&result[0]) +
			ItemPointerGetOffsetNumber(&result[decoded - 1]);
		pfree(result);
	}
	elapsed = cpu_ms() - begin;
	CHECK_FOR_INTERRUPTS();
	initStringInfo(&report);
	appendStringInfo(&report,
		"{\"name\":\"%s\",\"loops\":%d,\"items_per_loop\":%d,\"segments\":%d,\"compressed_bytes\":%d,\"decoder_allocation_materialization_free_cpu_ms\":%.9f,\"checksum\":\"" UINT64_FORMAT "\",\"consumed\":\"" UINT64_FORMAT "\"}",
		name, loops, c->nitems, segments, length, elapsed, checksum, consumed);
	pfree(encoded);
	pfree(expected);
	PG_RETURN_TEXT_P(cstring_to_text(report.data));
}
