				/* Otherwise scan to find the first item > advancePast */
				while (entry->matchOffsets[entry->offset] <= advancePastOff)
					entry->offset++;
