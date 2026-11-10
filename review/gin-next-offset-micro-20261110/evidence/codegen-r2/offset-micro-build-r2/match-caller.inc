				/* Keep zero- and one-offset advances on the short path. */
				if (entry->matchOffsets[entry->offset] <= advancePastOff)
				{
					entry->offset++;
					if (entry->matchOffsets[entry->offset] <= advancePastOff)
						entry->offset = ginAdvanceMatchOffsets(entry->matchOffsets,
																entry->offset + 1,
																entry->matchNtuples,
																advancePastOff);
				}
