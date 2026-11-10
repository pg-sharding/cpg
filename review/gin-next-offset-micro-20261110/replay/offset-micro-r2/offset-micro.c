/* Exact offset fragments with actual PostgreSQL types; this is not a full AM. */
#include "postgres.h"
#include "access/gin_private.h"
#include <time.h>
#include "match-helper.inc"
#undef printf

typedef int (*OffsetFragment) (GinScanEntry entry, OffsetNumber advancePastOff);

static pg_noinline int
offset_baseline(GinScanEntry entry, OffsetNumber advancePastOff)
{
	if (entry->matchOffsets[entry->matchNtuples - 1] <= advancePastOff)
		return entry->matchNtuples;
#include "baseline-caller.inc"
	return entry->offset;
}

static pg_noinline int
offset_candidate(GinScanEntry entry, OffsetNumber advancePastOff)
{
	if (entry->matchOffsets[entry->matchNtuples - 1] <= advancePastOff)
		return entry->matchNtuples;
#include "match-caller.inc"
	return entry->offset;
}

static uint64
nanoseconds(clockid_t clock)
{
	struct timespec ts;

	if (clock_gettime(clock, &ts) != 0)
		exit(15);
	return (uint64) ts.tv_sec * UINT64CONST(1000000000) + ts.tv_nsec;
}

int
main(int argc, char **argv)
{
	int selector;
	int n;
	int skip;
	int loops;
	GinScanEntryData entry;
	OffsetNumber threshold;
	OffsetFragment volatile invoke;
	uint64 checksum = 0;
	uint64 cpu_start;
	uint64 wall_start;
	uint64 cpu;
	uint64 wall;

	if (argc != 5)
		return 10;
	selector = atoi(argv[1]);
	n = atoi(argv[2]);
	skip = atoi(argv[3]);
	loops = atoi(argv[4]);
	if ((selector != 0 && selector != 1) || n < 1 || n > TBM_MAX_TUPLES_PER_PAGE ||
		skip < 0 || skip >= n || loops != 250000)
		return 11;
	StaticAssertStmt(sizeof(OffsetNumber) == 2, "uint16 offsets required");
	entry.matchNtuples = n;
	for (int i = 0; i < n; i++)
		entry.matchOffsets[i] = i + 1;
	threshold = skip;
	invoke = selector ? offset_candidate : offset_baseline;
	entry.offset = 0;
	if (invoke(&entry, threshold) != skip)
		return 12;

	/* Common volatile indirect call prevents loop hoisting/devirtualization. */
	cpu_start = nanoseconds(CLOCK_PROCESS_CPUTIME_ID);
	wall_start = nanoseconds(CLOCK_MONOTONIC);
	for (int i = 0; i < loops; i++)
	{
		entry.offset = 0;
		checksum += invoke(&entry, threshold);
	}
	wall = nanoseconds(CLOCK_MONOTONIC) - wall_start;
	cpu = nanoseconds(CLOCK_PROCESS_CPUTIME_ID) - cpu_start;
	if (checksum != (uint64) skip * loops || cpu == 0 || wall == 0)
		return 13;
	printf("{\"status\":\"PASS_OFFSET_FRAGMENT\",\"n\":%d,\"skip\":%d,\"loops\":%d,\"checksum\":%llu,\"cpu_ns\":%llu,\"wall_ns\":%llu}\n",
		   n, skip, loops, (unsigned long long) checksum,
		   (unsigned long long) cpu, (unsigned long long) wall);
	return 0;
}
