static bool
ginRequiredHeapGetItem(GinState *ginstate, GinScanKey key,
					   ItemPointerData advancePast, ItemPointerData *minItem)
{
	GinRequiredHeapItem *heap = key->requiredHeap;

	for (;;)
	{
		GinScanEntry entry = heap[0].entry;
		ItemPointerData current;

		CHECK_FOR_INTERRUPTS();
		if (entry->isFinished)
			ItemPointerSetMax(&current);
		else
			current = entry->curItem;
		Assert(ginCompareItemPointers(&heap[0].item, &current) <= 0);
		if (ginCompareItemPointers(&heap[0].item, &current) != 0)
		{
			heap[0].item = current;
			ginRequiredHeapSiftDown(heap, key->nrequired, 0);
			continue;
		}
		if (entry->isFinished)
			return false;
		if (ginCompareItemPointers(&current, &advancePast) > 0)
		{
			*minItem = current;
			return true;
		}

		entryGetItem(ginstate, entry, advancePast);
		if (entry->isFinished)
			ItemPointerSetMax(&heap[0].item);
		else
			heap[0].item = entry->curItem;
		ginRequiredHeapSiftDown(heap, key->nrequired, 0);
	}
}
