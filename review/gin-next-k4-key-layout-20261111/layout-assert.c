/* Compile-only layout probe; no backend is linked or started. */
#include "postgres.h"
#include "access/gin_private.h"
#include <stddef.h>

_Static_assert(sizeof(void *) == 8, "This probe describes the measured 64-bit ABI");
_Static_assert(sizeof(GinScanKeyData) == EXPECT_SIZE, "GinScanKeyData size");
_Static_assert(offsetof(GinScanKeyData, nrequired) == 24, "nrequired offset");
_Static_assert(offsetof(GinScanKeyData, additionalEntries) == 32, "additionalEntries offset");
_Static_assert(offsetof(GinScanKeyData, nadditional) == EXPECT_NADDITIONAL, "nadditional offset");
_Static_assert(offsetof(GinScanKeyData, entryRes) == EXPECT_ENTRYRES, "entryRes offset");
_Static_assert(offsetof(GinScanKeyData, triConsistentFn) == EXPECT_TRI_FN, "triConsistentFn offset");
_Static_assert(offsetof(GinScanKeyData, strategy) == EXPECT_STRATEGY, "strategy offset");
#ifdef EXPECT_CACHE
_Static_assert(offsetof(GinScanKeyData, triCache) == EXPECT_CACHE, "triCache offset");
#endif
