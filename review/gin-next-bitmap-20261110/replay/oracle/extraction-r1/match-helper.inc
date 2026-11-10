static inline int
ginAdvanceMatchOffsets(const OffsetNumber *offsets, int offset, int ntuples,
					   OffsetNumber advancePast)
{
	int			lower;
	int			upper = ntuples;
	int			step = 1;
	int			remaining = ntuples - offset;

	Assert(offset >= 0 && offset < ntuples);
	Assert(offsets[ntuples - 1] > advancePast);
	if (offsets[offset] > advancePast)
		return offset;

	lower = offset + 1;
	while (step < remaining)
	{
		int			probe = offset + step;

		if (offsets[probe] > advancePast)
		{
			upper = probe;
			break;
		}
		lower = probe + 1;
		if (step > remaining / 2)
			break;
		step *= 2;
	}

	while (lower < upper)
	{
		int			middle = lower + (upper - lower) / 2;

		if (offsets[middle] <= advancePast)
			lower = middle + 1;
		else
			upper = middle;
	}
	return lower;
}
