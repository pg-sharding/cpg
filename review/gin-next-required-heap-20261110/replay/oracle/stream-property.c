/* Deterministic valid streams with actual PG types; not a replacement AM. */
#include "postgres.h"
#include "access/gin_private.h"
#include "miscadmin.h"
#undef printf

/* Interrupt processing is exercised by full backend tests, not this fragment. */
#undef CHECK_FOR_INTERRUPTS
#define CHECK_FOR_INTERRUPTS() ((void) 0)

#define STREAM_ITEMS 24
typedef struct OracleStream
{
	GinScanEntryData entry;
	ItemPointerData items[STREAM_ITEMS];
	int cursor;
} OracleStream;

static uint64 advances;
static uint64 finishes;

static uint64
value(const ItemPointerData *item)
{
	return (uint64) GinItemPointerGetBlockNumber(item) * UINT64CONST(65536) +
		GinItemPointerGetOffsetNumber(item);
}

static void
entryGetItem(GinState *ginstate, GinScanEntry entry, ItemPointerData past)
{
	OracleStream *stream = (OracleStream *) entry;

	(void) ginstate;
	advances++;
	while (stream->cursor < STREAM_ITEMS && value(&stream->items[stream->cursor]) <= value(&past))
		stream->cursor++;
	if (stream->cursor == STREAM_ITEMS)
	{
		entry->isFinished = true;
		ItemPointerSetInvalid(&entry->curItem);
		finishes++;
	}
	else
		entry->curItem = stream->items[stream->cursor++];
}

#include "heap-sift.inc"
#include "heap-select.inc"

/* Independent linear selection, with a separate copy of every entry state. */
static bool
reference(OracleStream *streams, const int *ids, int n,
		  ItemPointerData past, ItemPointerData *result)
{
	uint64 best = UINT64CONST(0xffffffffffff);
	bool found = false;

	for (int i = 0; i < n; i++)
	{
		OracleStream *s = &streams[ids[i]];

		if (s->entry.isFinished)
			continue;
		if (value(&s->entry.curItem) <= value(&past))
		{
			while (s->cursor < STREAM_ITEMS && value(&s->items[s->cursor]) <= value(&past))
				s->cursor++;
			if (s->cursor == STREAM_ITEMS)
			{
				s->entry.isFinished = true;
				ItemPointerSetInvalid(&s->entry.curItem);
				continue;
			}
			s->entry.curItem = s->items[s->cursor++];
		}
		if (value(&s->entry.curItem) < best)
		{
			best = value(&s->entry.curItem);
			*result = s->entry.curItem;
			found = true;
		}
	}
	return found;
}

int
main(void)
{
	const int widths[] = {1, 2, 7, 8, 32, 128, 512};
	uint64 checks = 0;
	uint64 equal_minima = 0;
	uint64 stale_nonroots = 0;
	uint64 checksum = 0;

	for (int w = 0; w < (int) lengthof(widths); w++)
		for (int scenario = 0; scenario < 4; scenario++)
		{
			int n = widths[w];
			int total = n + (n + 1) / 2;
			OracleStream *actual = calloc(total, sizeof(OracleStream));
			OracleStream *refs = calloc(total, sizeof(OracleStream));
			GinScanKeyData keys[2] = {{0}};
			int *ids[2];
			ItemPointerData last[2];
			bool done[2] = {false, false};

			if (!actual || !refs)
				return 10;
			for (int s = 0; s < total; s++)
			{
				ItemPointerSetMin(&actual[s].entry.curItem);
				for (int j = 0; j < STREAM_ITEMS; j++)
				{
					BlockNumber block = 1 + j * (scenario == 0 ? 1 : scenario == 1 ? 2 : 17) +
						(scenario == 0 ? 0 : s % (scenario == 1 ? 2 : 7));
					OffsetNumber off = 1 + s % 4;

					if (scenario == 1 && j % 5 == 0)
						ItemPointerSetLossyPage(&actual[s].items[j], block);
					else
						ItemPointerSet(&actual[s].items[j], block, off);
				}
			}
			memcpy(refs, actual, total * sizeof(OracleStream));
			for (int k = 0; k < 2; k++)
			{
				ids[k] = calloc(n, sizeof(int));
				keys[k].nrequired = n;
				keys[k].requiredHeap = calloc(n, sizeof(GinRequiredHeapItem));
				if (!ids[k] || !keys[k].requiredHeap)
					return 11;
				ItemPointerSetMin(&last[k]);
				for (int i = 0; i < n; i++)
				{
					ids[k][i] = k == 0 || i < n / 2 ? i : n + i - n / 2;
					keys[k].requiredHeap[i].entry = &actual[ids[k][i]].entry;
					keys[k].requiredHeap[i].item = actual[ids[k][i]].entry.curItem;
				}
				for (int i = n / 2; i > 0; i--)
					ginRequiredHeapSiftDown(keys[k].requiredHeap, n, i - 1);
			}
			for (int step = 0; step < 400 && !(done[0] && done[1]); step++)
			{
				int k = step % 2;
				ItemPointerData past = last[k];
				ItemPointerData expected;
				ItemPointerData got;
				bool want;
				bool have;

				if (done[k])
					continue;
				if (step % 13 == 5)
				{
					ItemPointerData jump;

					ItemPointerSet(&jump, step * 3 + 1, 0);
					if (value(&jump) > value(&past))
						past = jump;
				}
				for (int i = 1; i < n; i++)
				{
					GinRequiredHeapItem *node = &keys[k].requiredHeap[i];

					if (node->entry->isFinished || value(&node->item) < value(&node->entry->curItem))
						stale_nonroots++;
				}
				want = reference(refs, ids[k], n, past, &expected);
				have = ginRequiredHeapGetItem(NULL, &keys[k], past, &got);
				if (want != have || (want && value(&got) != value(&expected)))
					return 12;
				for (int s = 0; s < total; s++)
					if (actual[s].cursor != refs[s].cursor ||
						actual[s].entry.isFinished != refs[s].entry.isFinished ||
						value(&actual[s].entry.curItem) != value(&refs[s].entry.curItem))
						return 13;
				checks++;
				done[k] = !have;
				if (have)
				{
					int equal = 0;

					last[k] = got;
					checksum += value(&got);
					for (int i = 0; i < n; i++)
						if (!actual[ids[k][i]].entry.isFinished &&
							value(&actual[ids[k][i]].entry.curItem) == value(&got))
							equal++;
					if (equal > 1)
						equal_minima++;
				}
			}
			if (!(done[0] && done[1]))
				return 14;
			for (int k = 0; k < 2; k++)
			{
				free(ids[k]);
				free(keys[k].requiredHeap);
			}
			free(actual);
			free(refs);
		}
	if (!equal_minima || !stale_nonroots || !finishes)
		return 15;
	printf("{\"status\":\"PASS_VALID_SHARED_STREAM_FRAGMENTS\",\"checks\":%llu,\"equal_minima\":%llu,\"stale_nonroots\":%llu,\"advances\":%llu,\"finishes\":%llu,\"checksum\":%llu}\n",
		   (unsigned long long) checks, (unsigned long long) equal_minima,
		   (unsigned long long) stale_nonroots, (unsigned long long) advances,
		   (unsigned long long) finishes, (unsigned long long) checksum);
	return 0;
}
