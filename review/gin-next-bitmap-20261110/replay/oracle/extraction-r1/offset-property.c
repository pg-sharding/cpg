/* Valid exact-page offset fragments; this is not an AM replacement. */
#include "postgres.h"
#include "access/htup_details.h"
#include "nodes/tidbitmap.h"
#include "storage/off.h"
#include "match-helper.inc"
#undef printf

typedef struct OracleEntry
{
	OffsetNumber matchOffsets[TBM_MAX_TUPLES_PER_PAGE];
	int offset;
	int matchNtuples;
} OracleEntry;

static int
candidate(OracleEntry *entry, OffsetNumber advancePastOff)
{
	if (entry->offset == entry->matchNtuples)
		return entry->offset;
	/* The production page-exhaustion test precedes the copied short path. */
	if (entry->matchOffsets[entry->matchNtuples - 1] <= advancePastOff)
		return entry->matchNtuples;
#include "match-caller.inc"
	return entry->offset;
}

int
main(void)
{
	OracleEntry entry;
	uint64 checked = 0;
	uint64 helper_checked = 0;
	uint64 skip[6] = {0};
	uint64 checksum = 0;

	StaticAssertStmt(sizeof(OffsetNumber) == 2, "uint16 offsets required");
	for (int n = 1; n <= TBM_MAX_TUPLES_PER_PAGE; n++)
		for (int pattern = 0; pattern < 4; pattern++)
		{
			entry.matchNtuples = n;
			for (int i = 0; i < n; i++)
			{
				unsigned offset;

				if (pattern == 0)
					offset = i + 1;
				else if (pattern == 1)
					offset = MaxOffsetNumber - n + i + 1;
				else if (pattern == 2)
					offset = 1 + (unsigned) i * (MaxOffsetNumber - 1) / Max(n - 1, 1);
				else
					offset = 1 + (unsigned) (i + 1) * (MaxOffsetNumber - 1) / (n + 1);
				entry.matchOffsets[i] = offset;
				if (!OffsetNumberIsValid(offset) ||
					(i && entry.matchOffsets[i - 1] >= offset))
					return 10;
			}
			/* Every valid page offset threshold, including zero and max. */
			for (int threshold = 0; threshold <= MaxOffsetNumber; threshold++)
			{
				int first = 0;

				/* Independent linear reference, outside the cursor loop. */
				while (first < n && entry.matchOffsets[first] <= threshold)
					first++;
				for (int cursor = 0; cursor <= n; cursor++)
				{
					int expected = Max(first, cursor);
					int distance = expected - cursor;
					int bucket = distance <= 2 ? distance : distance == 4 ? 3 : distance < 16 ? 4 : 5;

					entry.offset = cursor;
					if (candidate(&entry, threshold) != expected)
					{
						printf("{\"status\":\"FAIL\",\"n\":%d,\"pattern\":%d,\"threshold\":%d,\"cursor\":%d,\"expected\":%d,\"actual\":%d}\n",
							   n, pattern, threshold, cursor, expected, entry.offset);
						return 11;
					}
					checked++;
					skip[bucket]++;
					checksum += (uint64) expected + threshold + cursor;
					if (cursor < n && first < n)
					{
						if (ginAdvanceMatchOffsets(entry.matchOffsets, cursor, n, threshold) != expected)
							return 12;
						helper_checked++;
					}
				}
			}
		}
	for (int i = 0; i < 6; i++)
		if (!skip[i])
			return 13;
	printf("{\"status\":\"PASS_VALID_OFFSET_FRAGMENTS\",\"checked\":%llu,\"helper_checked\":%llu,\"max_ntuples\":%d,\"max_offset\":%d,\"checksum\":%llu,\"skip_0_1_2_4_other_large\":[%llu,%llu,%llu,%llu,%llu,%llu]}\n",
		   (unsigned long long) checked, (unsigned long long) helper_checked,
		   TBM_MAX_TUPLES_PER_PAGE, MaxOffsetNumber, (unsigned long long) checksum,
		   (unsigned long long) skip[0], (unsigned long long) skip[1],
		   (unsigned long long) skip[2], (unsigned long long) skip[3],
		   (unsigned long long) skip[4], (unsigned long long) skip[5]);
	return 0;
}
