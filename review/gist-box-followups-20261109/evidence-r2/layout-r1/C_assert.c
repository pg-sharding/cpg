#include "postgres.h"
#include "access/gist_private.h"
char scan_state_size[sizeof(GISTScanOpaqueData)];
char distances_offset[offsetof(GISTScanOpaqueData, distances)];
char page_data_offset[offsetof(GISTScanOpaqueData, pageData)];
char box_candidate_offset[offsetof(GISTScanOpaqueData, boxBatchCandidate)];
