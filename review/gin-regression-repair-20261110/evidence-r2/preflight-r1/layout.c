#include "postgres.h"
#include "access/gin_private.h"
#undef printf
int main(void)
{
printf("{\"bytes\":%zu", sizeof(GinScanEntryData));
printf(",\"queryKey\":%zu", offsetof(GinScanEntryData, queryKey));
printf(",\"queryCategory\":%zu", offsetof(GinScanEntryData, queryCategory));
printf(",\"isPartialMatch\":%zu", offsetof(GinScanEntryData, isPartialMatch));
printf(",\"extra_data\":%zu", offsetof(GinScanEntryData, extra_data));
printf(",\"strategy\":%zu", offsetof(GinScanEntryData, strategy));
printf(",\"searchMode\":%zu", offsetof(GinScanEntryData, searchMode));
printf(",\"attnum\":%zu", offsetof(GinScanEntryData, attnum));
printf(",\"buffer\":%zu", offsetof(GinScanEntryData, buffer));
printf(",\"curItem\":%zu", offsetof(GinScanEntryData, curItem));
printf(",\"matchBitmap\":%zu", offsetof(GinScanEntryData, matchBitmap));
printf(",\"matchIterator\":%zu", offsetof(GinScanEntryData, matchIterator));
printf(",\"matchResult\":%zu", offsetof(GinScanEntryData, matchResult));
printf(",\"matchOffsets\":%zu", offsetof(GinScanEntryData, matchOffsets));
printf(",\"matchNtuples\":%zu", offsetof(GinScanEntryData, matchNtuples));
printf(",\"list\":%zu", offsetof(GinScanEntryData, list));
printf(",\"nlist\":%zu", offsetof(GinScanEntryData, nlist));
printf(",\"offset\":%zu", offsetof(GinScanEntryData, offset));
printf(",\"isFinished\":%zu", offsetof(GinScanEntryData, isFinished));
printf(",\"reduceResult\":%zu", offsetof(GinScanEntryData, reduceResult));
printf(",\"predictNumberResult\":%zu", offsetof(GinScanEntryData, predictNumberResult));
printf(",\"btree\":%zu", offsetof(GinScanEntryData, btree));
puts("}");
return 0;
}
