static void
ginRequiredHeapSiftDown(GinRequiredHeapItem *heap, int count, int root)
{
	GinRequiredHeapItem item = heap[root];
	int			child;

	while ((child = root * 2 + 1) < count)
	{
		if (child + 1 < count &&
			ginCompareItemPointers(&heap[child + 1].item, &heap[child].item) < 0)
			child++;
		if (ginCompareItemPointers(&item.item, &heap[child].item) <= 0)
			break;
		heap[root] = heap[child];
		root = child;
	}
	heap[root] = item;
}
