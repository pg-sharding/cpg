/*-------------------------------------------------------------------------
 *
 * verify_hash.c
 *		Verifies the integrity of hash indexes based on invariants.
 *
 * Hash index verification checks a number of invariants:
 *
 * - metapage: the magic number and version must be correct, the bucket
 *   masks must be self-consistent, the spare-page counters must be
 *   monotonic, and the free-space bitmap page addresses must be distinct
 *   and in range.
 *
 * - bucket chains: for every bucket 0..maxbucket, the primary bucket page
 *   (located via BUCKET_TO_BLKNO) must be a bucket page belonging to that
 *   bucket, and the chain of overflow pages must be well-formed: all pages
 *   after the primary are overflow pages of the same bucket, back links
 *   are consistent, and the chain contains no cycles.
 *
 * - item placement: the 32-bit hash value stored in each index tuple must
 *   map to the bucket the tuple resides in, under the split-tolerant rule
 *   documented below (see hash_item_bucket_ok()).
 *
 * - overflow bitmaps: every overflow page linked in a bucket chain must be
 *   marked in-use in the free-space bitmaps.
 *
 * Concurrency: the check runs under only AccessShareLock on the index,
 * matching what gin_index_check() uses.  While checking a single bucket,
 * the checker holds a shared buffer lock on the primary bucket page, which
 * prevents concurrent splits and bucket squeeze on that bucket (both need
 * a cleanup lock on that page), making the chain structure and the in-use
 * bitmap expectation of that bucket stable for the duration of the walk.
 * Concurrent inserts into other buckets are tolerated by design: the
 * metapage is re-read under a shared buffer lock wherever freshness
 * matters, and the item placement check is intentionally split-tolerant.
 *
 * Portions Copyright (c) 1996-2026, PostgreSQL Global Development Group
 *
 * IDENTIFICATION
 *	  contrib/amcheck/verify_hash.c
 *
 *-------------------------------------------------------------------------
 */
#include "postgres.h"

#include "access/hash.h"
#include "access/itup.h"
#include "access/table.h"
#include "catalog/index.h"
#include "catalog/pg_am.h"
#include "miscadmin.h"
#include "storage/bufmgr.h"
#include "storage/bufpage.h"
#include "storage/lockdefs.h"
#include "utils/builtins.h"
#include "utils/errcodes.h"
#include "utils/guc.h"
#include "utils/rel.h"

/*
 * Working copy of the metapage contents.  The real metapage can change
 * concurrently (splits, overflow page allocation), so the checker copies
 * it into a private snapshot under a shared buffer lock and works from
 * the copy.  The snapshot is refreshed where freshness matters (once per
 * bucket, and for bitmap page lookups).
 */
typedef struct HashCheckState
{
	Relation	rel;
	Relation	heaprel;		/* locked/opened by hash_index_check(), PG14-style amcheck */
	HashMetaPageData metacopy;
	BufferAccessStrategy strategy;
} HashCheckState;

/*
 * Upper bound on the number of pages that can be visited while walking a
 * single bucket chain.  The visited-block array is allocated with this
 * many (or more, see the relation size at allocation time) entries, so a
 * legitimate chain can never hit the limit: it cannot be longer than the
 * relation, and the array is sized to the larger of the two.
 */
#define MAX_CHAIN_PAGES		(64 * 1024)

static void hash_index_checkable(Relation rel);
static void hash_check_index(Relation rel, Relation heaprel);
static void hash_read_meta_copy(HashCheckState *state);
static void hash_check_metapage(HashCheckState *state);
static void hash_check_all_buckets(HashCheckState *state);
static void hash_check_bucket(HashCheckState *state, Bucket bucket);
static Page hash_read_page_checked(HashCheckState *state, BlockNumber blkno,
								   Buffer *buffer);
static bool hash_page_header_valid(Page page);
static void hash_check_heap_tid(HashCheckState *state, IndexTuple itup,
							   OffsetNumber itup_off, BlockNumber itup_blk);
static void hash_check_page_items(HashCheckState *state, Page page,
								  BlockNumber blkno, Bucket bucket);
static void hash_check_ovfl_bitmap(HashCheckState *state,
								   BlockNumber ovflblkno);

/*
 * Verify that the heap tid referenced by a stored index tuple points to
 * a real heap line pointer.
 *
 * A production report showed hash indexes referencing tids past a heap
 * page's line pointer array; catch that class explicitly, separate from
 * the structural checks above.
 *
 * Concurrency / false-positive discipline (PoC choices, documented):
 *
 * - The heap relation is opened and locked by our caller
 *   (hash_index_check()) with AccessShareLock, matching what
 *   bt_index_check's heapallindexed path uses, so the heap cannot be
 *   truncated underneath us; it can only grow.
 *
 * - The heap size is snapshotted here once per index page.  Any index
 *   tuple visible on that page was written after the heap block it
 *   references was allocated, and the snapshot is taken before the page
 *   is read, so the block range check cannot misfire.  The reverse
 *   direction (a concurrently extended heap letting genuinely corrupt
 *   tids pass transiently) is accepted for the PoC: they would be
 *   caught by the next run, and re-reading the heap size per tuple
 *   would buy almost nothing under the same race.
 *
 * - Only the boundary is checked (tid offnum <= MaxOffsetNumber of the
 *   heap page).  The line pointer's lp_state (unused/dead) is
 *   deliberately NOT treated as an error: concurrent vacuum can
 *   legitimately mark line pointers dead/unused, which would make any
 *   state check false-positive under ordinary churn.
 *
 * - The heap buffer is pinned, read and released immediately; nothing
 *   is cached across buckets and memory stays bounded.
 */
static void
hash_check_heap_tid(HashCheckState *state, IndexTuple itup,
				   OffsetNumber itup_off, BlockNumber itup_blk)
{
	Relation	heaprel = state->heaprel;
	ItemPointer	tid = &itup->t_tid;
	BlockNumber	tid_blk = ItemPointerGetBlockNumber(tid);
	OffsetNumber tid_off = ItemPointerGetOffsetNumber(tid);
	BlockNumber	heapnblocks;
	Buffer		buffer;
	Page		page;
	OffsetNumber maxoff;

	/* no heap relation: e.g. hash index on a foreign/nonheap? cannot happen, play safe */
	if (heaprel == NULL)
		return;

	heapnblocks = RelationGetNumberOfBlocks(heaprel);

	if (tid_blk >= heapnblocks)
		ereport(ERROR,
				(errcode(ERRCODE_INDEX_CORRUPTED),
				 errmsg("heap tid from index tuple (%u,%u) points past end of heap at offset %u of block %u in index \"%s\"",
						tid_blk, tid_off, itup_off, itup_blk,
						RelationGetRelationName(state->rel)),
				 errdetail_internal("Heap size is %u blocks.", heapnblocks)));

	buffer = ReadBufferExtended(heaprel, MAIN_FORKNUM, tid_blk,
								RBM_NORMAL, state->strategy);
	LockBuffer(buffer, BUFFER_LOCK_SHARE);
	page = BufferGetPage(buffer);
	maxoff = PageGetMaxOffsetNumber(page);
	UnlockReleaseBuffer(buffer);

	/* first offset is 1; a zero offnum is never a valid line pointer */
	if (tid_off == 0 || tid_off > maxoff)
		ereport(ERROR,
				(errcode(ERRCODE_INDEX_CORRUPTED),
				 errmsg("heap tid from index tuple (%u,%u) points past end of heap page line pointer array at offset %u of block %u in index \"%s\"",
						tid_blk, tid_off, itup_off, itup_blk,
						RelationGetRelationName(state->rel)),
				 errdetail_internal("Heap page has %u line pointers.",
									maxoff)));
}

/*
 * hash_index_check(index regclass)
 *
 * Verify integrity of a hash index.
 *
 * Acquires AccessShareLock on heap & index relations.
 */
PG_FUNCTION_INFO_V1(hash_index_check);

Datum
hash_index_check(PG_FUNCTION_ARGS)
{
	Oid			indrelid = PG_GETARG_OID(0);
	Relation	indrel;
	Relation	heaprel;
	Oid			heapid;
	Oid			save_userid;
	int			save_sec_context;
	int			save_nestlevel;

	/*
	 * We must lock table before index to avoid deadlocks.  However, if the
	 * passed indrelid isn't an index then IndexGetRelation() will fail.
	 * Rather than emitting a not-very-helpful error message, postpone
	 * complaining, expecting that the is-it-an-index test below will fail.
	 */
	heapid = IndexGetRelation(indrelid, true);
	if (OidIsValid(heapid))
	{
		heaprel = table_open(heapid, AccessShareLock);

		/*
		 * Switch to the table owner's userid, so that any index functions
		 * are run as that user.  Also lock down security-restricted
		 * operations and arrange to make GUC variable changes local to
		 * this command.
		 */
		GetUserIdAndSecContext(&save_userid, &save_sec_context);
		SetUserIdAndSecContext(heaprel->rd_rel->relowner,
							   save_sec_context | SECURITY_RESTRICTED_OPERATION);
		save_nestlevel = NewGUCNestLevel();
		RestrictSearchPath();
	}
	else
	{
		heaprel = NULL;
		/* Set these just to suppress "uninitialized variable" warnings */
		save_userid = InvalidOid;
		save_sec_context = -1;
		save_nestlevel = -1;
	}

	/*
	 * Open the target index relations separately, with the heap relation
	 * locked first to prevent deadlocking.
	 */
	indrel = index_open(indrelid, AccessShareLock);

	/*
	 * Since we did the IndexGetRelation call above without any lock, it's
	 * barely possible that a race against an index drop/recreation could
	 * have netted us the wrong table.
	 */
	if (heaprel == NULL || heapid != IndexGetRelation(indrelid, false))
		ereport(ERROR,
				(errcode(ERRCODE_UNDEFINED_TABLE),
				 errmsg("could not open parent table of index \"%s\"",
						RelationGetRelationName(indrel))));

	/* Relation suitable for checking as a hash index? */
	hash_index_checkable(indrel);

	hash_check_index(indrel, heaprel);

	/* Roll back any GUC changes executed by index functions */
	AtEOXact_GUC(false, save_nestlevel);

	/* Restore userid and security context */
	SetUserIdAndSecContext(save_userid, save_sec_context);

	/*
	 * Release locks early.  That's ok here because nothing in the called
	 * routines will trigger shared cache invalidations to be sent.
	 */
	index_close(indrel, AccessShareLock);
	if (heaprel)
		table_close(heaprel, AccessShareLock);

	PG_RETURN_VOID();
}

/*
 * Check that the relation is a hash index that is safe to check.
 *
 * NB: Intentionally not checking permissions, the function is normally not
 * callable by non-superusers. If granted, it's useful to be able to check a
 * whole cluster.
 */
static void
hash_index_checkable(Relation rel)
{
	if (rel->rd_rel->relkind != RELKIND_INDEX ||
		rel->rd_rel->relam != HASH_AM_OID)
		ereport(ERROR,
				(errcode(ERRCODE_FEATURE_NOT_SUPPORTED),
				 errmsg("only hash indexes are supported as targets for verification"),
				 errdetail("Relation \"%s\" is not a hash index.",
						   RelationGetRelationName(rel))));

	if (RELATION_IS_OTHER_TEMP(rel))
		ereport(ERROR,
				(errcode(ERRCODE_FEATURE_NOT_SUPPORTED),
				 errmsg("cannot access temporary tables of other sessions"),
				 errdetail("Index \"%s\" is associated with temporary relation.",
						   RelationGetRelationName(rel))));

	if (!rel->rd_index->indisvalid)
		ereport(ERROR,
				(errcode(ERRCODE_FEATURE_NOT_SUPPORTED),
				 errmsg("cannot check index \"%s\"",
						RelationGetRelationName(rel)),
				 errdetail("Index is not valid.")));
}

/*
 * Main entry point for the actual verification.
 */
static void
hash_check_index(Relation rel, Relation heaprel)
{
	HashCheckState state;

	state.rel = rel;
	state.heaprel = heaprel;
	state.strategy = GetAccessStrategy(BAS_BULKREAD);

	hash_read_meta_copy(&state);
	hash_check_metapage(&state);
	hash_check_all_buckets(&state);
}

/*
 * Read block 0 and copy the metapage contents into state->metacopy.
 *
 * The buffer is only share-locked, so the copy is a consistent snapshot:
 * writers hold an exclusive buffer lock while updating the metapage, and
 * each logically-atomic update (masks/splitpoint, spares[], nmaps)
 * happens within a single critical section.
 */
static void
hash_read_meta_copy(HashCheckState *state)
{
	Buffer		metabuf;
	Page		page;
	HashPageOpaque opaque;

	metabuf = ReadBufferExtended(state->rel, MAIN_FORKNUM, HASH_METAPAGE,
								 RBM_NORMAL, state->strategy);
	LockBuffer(metabuf, BUFFER_LOCK_SHARE);
	page = BufferGetPage(metabuf);

	if (!hash_page_header_valid(page))
		ereport(ERROR,
				(errcode(ERRCODE_INDEX_CORRUPTED),
				 errmsg("index \"%s\": invalid metapage header",
						RelationGetRelationName(state->rel))));

	opaque = HashPageGetOpaque(page);
	if (opaque->hasho_page_id != HASHO_PAGE_ID ||
		(opaque->hasho_flag & LH_PAGE_TYPE) != LH_META_PAGE)
		ereport(ERROR,
				(errcode(ERRCODE_INDEX_CORRUPTED),
				 errmsg("index \"%s\": block 0 is not a hash metapage",
						RelationGetRelationName(state->rel))));

	memcpy(&state->metacopy, HashPageGetMeta(page),
		   sizeof(HashMetaPageData));

	UnlockReleaseBuffer(metabuf);
}

/*
 * Validate the metapage snapshot: magic, version, bucket masks, spare page
 * counters, and bitmap page count and addresses.
 */
static void
hash_check_metapage(HashCheckState *state)
{
	HashMetaPage metap = &state->metacopy;
	Relation	rel = state->rel;
	BlockNumber nblocks;
	uint32		ovflpoint;
	uint32		i;
	uint32		bitmap_pages_needed;

	if (metap->hashm_magic != HASH_MAGIC ||
		metap->hashm_version != HASH_VERSION)
		ereport(ERROR,
				(errcode(ERRCODE_INDEX_CORRUPTED),
				 errmsg("index \"%s\": corrupt hash metapage: wrong magic or version",
						RelationGetRelationName(rel)),
				 errdetail_internal("Magic 0x%08X, version %u; expected 0x%08X, version %u.",
									metap->hashm_magic,
									metap->hashm_version,
									HASH_MAGIC, HASH_VERSION)));

	ovflpoint = metap->hashm_ovflpoint;

	if (ovflpoint >= HASH_MAX_SPLITPOINTS)
		ereport(ERROR,
				(errcode(ERRCODE_INDEX_CORRUPTED),
				 errmsg("index \"%s\": metapage overflow point %u exceeds maximum",
						RelationGetRelationName(rel), ovflpoint)));

	/*
	 * Masks: highmask must be of the form 2^k-1, lowmask must be its lower
	 * half, and maxbucket must fit under highmask.  These fields change only
	 * together when a new splitpoint group is started, so the snapshot is
	 * internally consistent.
	 */
	if (metap->hashm_highmask == 0 ||
		(metap->hashm_highmask & (metap->hashm_highmask + 1)) != 0 ||
		metap->hashm_lowmask != (metap->hashm_highmask >> 1) ||
		(metap->hashm_maxbucket & metap->hashm_highmask) != metap->hashm_maxbucket)
		ereport(ERROR,
				(errcode(ERRCODE_INDEX_CORRUPTED),
				 errmsg("index \"%s\": metapage bucket masks are inconsistent",
						RelationGetRelationName(rel)),
				 errdetail_internal("maxbucket %u, highmask 0x%X, lowmask 0x%X.",
									metap->hashm_maxbucket,
									metap->hashm_highmask,
									metap->hashm_lowmask)));

	/*
	 * spares[] must be non-decreasing up to the current overflow point;
	 * entries beyond it must still be zero, since they are only set when the
	 * overflow point itself advances (see _hash_expandtable()).
	 */
	for (i = 0; i < ovflpoint; i++)
	{
		if (metap->hashm_spares[i] > metap->hashm_spares[i + 1])
			ereport(ERROR,
					(errcode(ERRCODE_INDEX_CORRUPTED),
					 errmsg("index \"%s\": metapage spare counters are not monotonic at splitpoint %u",
							RelationGetRelationName(rel), i),
					 errdetail_internal("spares[%u]=%u, spares[%u]=%u.",
										i, metap->hashm_spares[i],
										i + 1, metap->hashm_spares[i + 1])));
	}
	for (i = ovflpoint + 1; i < HASH_MAX_SPLITPOINTS; i++)
	{
		if (metap->hashm_spares[i] != 0)
			ereport(ERROR,
					(errcode(ERRCODE_INDEX_CORRUPTED),
					 errmsg("index \"%s\": metapage spare counter %u is set beyond the current overflow point %u",
							RelationGetRelationName(rel), i, ovflpoint)));
	}

	/*
	 * firstfree is an advisory hint (lowest-numbered possibly-free overflow
	 * page, as a 0-based bitmap bit number), but a value pointing past all
	 * pages allocated at the current splitpoint would make core code skip
	 * free pages forever.  Note the 1-based bias of spares[]:
	 * spares[ovflpoint] is one past the highest allocated bit, so firstfree
	 * == spares[ovflpoint] is still acceptable.
	 */
	if (metap->hashm_firstfree > metap->hashm_spares[ovflpoint])
		ereport(ERROR,
				(errcode(ERRCODE_INDEX_CORRUPTED),
				 errmsg("index \"%s\": metapage firstfree %u exceeds allocated overflow pages %u",
						RelationGetRelationName(rel),
						metap->hashm_firstfree,
						metap->hashm_spares[ovflpoint])));

	/*
	 * There must be enough bitmap pages to cover all overflow pages allocated
	 * so far.  Core code adds a bitmap page at the exact moment the preceding
	 * one would overflow, so being short is corruption, not a transient
	 * state.  Account for the 1-based bias of spares[]: the number of
	 * allocated overflow pages (and hence of used bitmap bits at the current
	 * splitpoint) is spares[ovflpoint] minus one.
	 */
	bitmap_pages_needed =
		(metap->hashm_spares[ovflpoint] - 1 + (BMPGSZ_BIT(metap) - 1)) >>
		BMPG_SHIFT(metap);
	if (metap->hashm_nmaps < bitmap_pages_needed ||
		metap->hashm_nmaps > HASH_MAX_BITMAPS)
		ereport(ERROR,
				(errcode(ERRCODE_INDEX_CORRUPTED),
				 errmsg("index \"%s\": metapage has %u bitmap pages, but at least %u are needed",
						RelationGetRelationName(rel),
						metap->hashm_nmaps, bitmap_pages_needed)));

	/*
	 * Bitmap page addresses must be within the relation (advisory under
	 * concurrent extension, which can only grow nblocks) and distinct.
	 */
	nblocks = RelationGetNumberOfBlocks(rel);
	for (i = 0; i < metap->hashm_nmaps; i++)
	{
		if (metap->hashm_mapp[i] == InvalidBlockNumber ||
			metap->hashm_mapp[i] >= nblocks)
			ereport(ERROR,
					(errcode(ERRCODE_INDEX_CORRUPTED),
					 errmsg("index \"%s\": bitmap page address %u is out of range",
							RelationGetRelationName(rel),
							metap->hashm_mapp[i])));
	}
	for (i = 0; i < metap->hashm_nmaps; i++)
	{
		uint32		j;

		for (j = i + 1; j < metap->hashm_nmaps; j++)
		{
			if (metap->hashm_mapp[i] == metap->hashm_mapp[j])
				ereport(ERROR,
						(errcode(ERRCODE_INDEX_CORRUPTED),
						 errmsg("index \"%s\": bitmap pages %u and %u have the same address %u",
								RelationGetRelationName(rel),
								i, j, metap->hashm_mapp[i])));
		}
	}
}

/*
 * Walk all buckets 0..maxbucket (as of a fresh metapage snapshot).  A
 * concurrent split may raise maxbucket while we run; buckets above the
 * snapshot are not checked, which is documented PoC behavior.
 */
static void
hash_check_all_buckets(HashCheckState *state)
{
	Bucket		maxbucket;
	Bucket		bucket;

	hash_read_meta_copy(state);

	maxbucket = state->metacopy.hashm_maxbucket;

	for (bucket = 0; bucket <= maxbucket; bucket++)
	{
		CHECK_FOR_INTERRUPTS();
		hash_check_bucket(state, bucket);
	}
}

/*
 * Basic page header sanity shared by all hash index pages.
 */
static bool
hash_page_header_valid(Page page)
{
	PageHeader	hdr = (PageHeader) page;

	if (hdr->pd_lower < (uint16) SizeOfPageHeaderData ||
		hdr->pd_upper < hdr->pd_lower ||
		hdr->pd_special < hdr->pd_upper ||
		hdr->pd_special > (uint16) BLCKSZ ||
		hdr->pd_special != MAXALIGN(hdr->pd_special) ||
		hdr->pd_special != (uint16) (BLCKSZ -
									 MAXALIGN(sizeof(HashPageOpaqueData))))
		return false;
	return true;
}

/*
 * Read one page and verify the basics shared by all hash index pages:
 * page header sanity and the hash page identifier.  The returned page
 * remains pinned and share-locked until the caller releases it.
 */
static Page
hash_read_page_checked(HashCheckState *state, BlockNumber blkno,
					   Buffer *buffer)
{
	Page		page;
	HashPageOpaque opaque;

	*buffer = ReadBufferExtended(state->rel, MAIN_FORKNUM, blkno,
								 RBM_NORMAL, state->strategy);
	LockBuffer(*buffer, BUFFER_LOCK_SHARE);
	page = BufferGetPage(*buffer);

	if (!hash_page_header_valid(page))
		ereport(ERROR,
				(errcode(ERRCODE_INDEX_CORRUPTED),
				 errmsg("index \"%s\": invalid page header on block %u",
						RelationGetRelationName(state->rel), blkno)));

	opaque = HashPageGetOpaque(page);
	if (opaque->hasho_page_id != HASHO_PAGE_ID)
		ereport(ERROR,
				(errcode(ERRCODE_INDEX_CORRUPTED),
				 errmsg("index \"%s\": invalid page opaque on block %u",
						RelationGetRelationName(state->rel), blkno),
				 errdetail_internal("Page identifier 0x%04X, expected 0x%04X.",
									opaque->hasho_page_id, HASHO_PAGE_ID)));

	return page;
}

/*
 * Does the stored hash value 'hashkey' validly reside in bucket
 * 'pagebucket'?
 *
 * Under the *current* metapage masks, a hash value maps to exactly one
 * home bucket (see _hash_hashkey2bucket()).  When a bucket splits, the
 * qualifying tuples are copied to the new bucket, but the originals stay
 * in the old bucket until the next split-cleanup for that bucket
 * (LH_BUCKET_NEEDS_SPLIT_CLEANUP).  Such garbage can persist for a long
 * time, and by then the metapage masks may have grown through several
 * further splits.  A strict "residency == current home" check would
 * therefore produce false positives.
 *
 * The tolerant rule used here: a tuple may reside in bucket B when B is a
 * prefix-bucket of its current home H, i.e., when B == H & (2^g - 1) for
 * some generation mask 2^g - 1 that is not larger than the current
 * highmask.  Every mask that any bucket mapping ever used has the form
 * 2^g - 1 (the low/high mask pair of some generation), and clamping by
 * the lowmask preserves the prefix shape, so every legitimate placement
 * satisfies this rule: at insert/cleanup time the stored bucket was the
 * home under the then-current masks, and the home only ever "narrows
 * down" to higher-precision prefixes of itself as the index grows.
 *
 * This intentionally loses the ability to detect stored-hash corruptions
 * that only alter bits at or above the prefix length implied by the
 * residing bucket; in particular, flipping high bits of a hash value
 * may go unnoticed if the low bits still fit the bucket.  A production
 * checker could tighten this if it recorded the masks current at the
 * last split-cleanup of each bucket.
 */
static bool
hash_item_bucket_ok(Bucket pagebucket, uint32 hashkey, uint32 maxbucket,
					uint32 highmask, uint32 lowmask)
{
	Bucket		home = _hash_hashkey2bucket(hashkey, maxbucket,
											highmask, lowmask);
	uint32		gen;

	if (home == pagebucket)
		return true;

	for (gen = 1; gen <= 32; gen++)
	{
		uint32		mask = (gen == 32) ? 0xFFFFFFFFU : ((1U << gen) - 1);

		/* masks larger than the current highmask were never realized */
		if (gen < 32 && mask > highmask)
			break;

		if ((uint32) pagebucket > mask)
			continue;
		if ((home & mask) == pagebucket)
			return true;
	}

	return false;
}

/*
 * Validate items on a hash page.  Every stored tuple must be a sane
 * IndexTuple, and its stored hash value must map to the bucket being
 * checked under the tolerant rule above.
 */
static void
hash_check_page_items(HashCheckState *state, Page page, BlockNumber blkno,
					  Bucket bucket)
{
	Relation	rel = state->rel;
	OffsetNumber maxoff = PageGetMaxOffsetNumber(page);
	OffsetNumber off;
	uint32		maxbucket = state->metacopy.hashm_maxbucket;
	uint32		highmask = state->metacopy.hashm_highmask;
	uint32		lowmask = state->metacopy.hashm_lowmask;
	OffsetNumber pd_special = ((PageHeader) page)->pd_special;

	for (off = FirstOffsetNumber; off <= maxoff; off++)
	{
		ItemId		iid;

		iid = PageGetItemId(page, off);

		/*
		 * Line pointers without storage are legitimately possible after index
		 * deletion.
		 */
		if (!ItemIdHasStorage(iid))
			continue;

		/*
		 * The item must reside strictly between the page header and the
		 * special area.
		 */
		if (ItemIdGetLength(iid) < (sizeof(IndexTupleData) +
									sizeof(uint32)) ||
			ItemIdGetOffset(iid) < SizeOfPageHeaderData ||
			(ItemIdGetOffset(iid) + ItemIdGetLength(iid)) > pd_special)
			ereport(ERROR,
					(errcode(ERRCODE_INDEX_CORRUPTED),
					 errmsg("index \"%s\": item storage is out of page bounds on page %u",
							RelationGetRelationName(rel), blkno),
					 errdetail_internal("Item %u has offset %u, length %u, special starts at %u.",
										off, ItemIdGetOffset(iid),
										ItemIdGetLength(iid), pd_special)));

		/* the stored tuple must be a sane hash index tuple ... */
		{
			IndexTuple	itup = (IndexTuple) PageGetItem(page, iid);
			uint32		hashkey;

			if ((uint32) IndexTupleSize(itup) != ItemIdGetLength(iid))
				ereport(ERROR,
						(errcode(ERRCODE_INDEX_CORRUPTED),
						 errmsg("index \"%s\": item size %u mismatches line pointer length %u on page %u",
								RelationGetRelationName(rel),
								(uint32) IndexTupleSize(itup),
								ItemIdGetLength(iid), blkno)));

			/* cross-check the referenced heap tid, separate from structural checks */
			hash_check_heap_tid(state, itup, off, blkno);

			hashkey = _hash_get_indextuple_hashkey(itup);

			/* ... whose only attribute is the raw 32-bit hash value */
			if (!hash_item_bucket_ok(bucket, hashkey, maxbucket,
									 highmask, lowmask))
				ereport(ERROR,
						(errcode(ERRCODE_INDEX_CORRUPTED),
						 errmsg("index \"%s\": item in bucket %u on page %u has hash value 0x%08X that belongs to bucket %u",
								RelationGetRelationName(rel),
								bucket, blkno, hashkey,
								_hash_hashkey2bucket(hashkey, maxbucket,
													 highmask, lowmask))));
		}
	}
}

/*
 * Verify that overflow page 'ovflblkno' is marked in-use in the free-pool
 * bitmaps.  While the caller holds a shared buffer lock on the primary
 * bucket page, the overflow pages of that bucket cannot be freed (freeing
 * requires a cleanup lock on the primary page), so the in-use expectation
 * is stable across concurrent maintenance elsewhere in the index.
 */
static void
hash_check_ovfl_bitmap(HashCheckState *state, BlockNumber ovflblkno)
{
	Relation	rel = state->rel;
	HashMetaPageData savedcopy;
	uint32		splitnum;
	uint32		i;
	uint32		ovflbitno = 0;
	bool		found = false;
	uint32		bitmappage;
	uint32		bitmapbit;
	BlockNumber bitmapblkno;
	Buffer		buffer;
	Page		page;
	HashPageOpaque opaque;
	uint32	   *freep;

	savedcopy = state->metacopy;

	/*
	 * Convert the overflow block number to a bitmap bit number, following
	 * _hash_ovflblkno_to_bitno(), but reporting corruption where core code
	 * reports a bogus call.
	 *
	 * The caller's metapage snapshot can be older than the page itself: an
	 * overflow page concurrently appended to this very chain is legitimately
	 * not covered by the spares[] values we snapshotted. Core code updates
	 * spares[] in the same critical section in which it adds the page to the
	 * bitmap and (only afterwards) the page is linked into a chain, so a
	 * metapage snapshot taken after we observed the link is guaranteed to
	 * cover the page.  Therefore, on a miss we refresh the snapshot once and
	 * only then complain.
	 */
	for (i = 0; i < 2 && !found; i++)
	{
		if (i == 1)
			hash_read_meta_copy(state);

		splitnum = state->metacopy.hashm_ovflpoint;
		{
			uint32		splitidx;

			for (splitidx = 1; splitidx <= splitnum; splitidx++)
			{
				uint32		bitnum;

				if (ovflblkno <= (BlockNumber) _hash_get_totalbuckets(splitidx))
					break;
				bitnum = ovflblkno - _hash_get_totalbuckets(splitidx);
				if (bitnum > state->metacopy.hashm_spares[splitidx - 1] &&
					bitnum <= state->metacopy.hashm_spares[splitidx])
				{
					ovflbitno = bitnum - 1;
					found = true;
					break;
				}
			}
		}
	}

	if (!found)
	{
		state->metacopy = savedcopy;
		ereport(ERROR,
				(errcode(ERRCODE_INDEX_CORRUPTED),
				 errmsg("index \"%s\": overflow page %u cannot be located in the free-page bitmap",
						RelationGetRelationName(rel), ovflblkno)));
	}

	/*
	 * The bit number of an existing page is stable, but nmaps/mapp[] can
	 * advance concurrently; the snapshot we now hold was taken after the page
	 * was linked (see above), so it covers the bitmap page, if any.
	 */
	bitmappage = ovflbitno >> BMPG_SHIFT(&state->metacopy);
	bitmapbit = ovflbitno & BMPG_MASK(&state->metacopy);

	if (bitmappage >= state->metacopy.hashm_nmaps)
	{
		state->metacopy = savedcopy;
		ereport(ERROR,
				(errcode(ERRCODE_INDEX_CORRUPTED),
				 errmsg("index \"%s\": overflow page %u references nonexistent bitmap page %u",
						RelationGetRelationName(rel), ovflblkno,
						bitmappage)));
	}

	bitmapblkno = state->metacopy.hashm_mapp[bitmappage];
	state->metacopy = savedcopy;

	buffer = ReadBufferExtended(rel, MAIN_FORKNUM, bitmapblkno,
								RBM_NORMAL, state->strategy);
	LockBuffer(buffer, BUFFER_LOCK_SHARE);
	page = BufferGetPage(buffer);

	opaque = HashPageGetOpaque(page);
	if (opaque->hasho_page_id != HASHO_PAGE_ID ||
		(opaque->hasho_flag & LH_PAGE_TYPE) != LH_BITMAP_PAGE)
		ereport(ERROR,
				(errcode(ERRCODE_INDEX_CORRUPTED),
				 errmsg("index \"%s\": block %u is supposed to be an overflow bitmap page, but is not",
						RelationGetRelationName(rel), bitmapblkno)));

	freep = HashPageGetBitmap(page);
	if (!ISSET(freep, bitmapbit))
		ereport(ERROR,
				(errcode(ERRCODE_INDEX_CORRUPTED),
				 errmsg("index \"%s\": overflow page %u is linked in a bucket chain, but is marked free in the bitmap",
						RelationGetRelationName(rel), ovflblkno)));

	UnlockReleaseBuffer(buffer);
}

/*
 * Check one bucket: locate the primary page via BUCKET_TO_BLKNO, verify
 * it, then walk the chain of overflow pages, verifying structure, items,
 * and bitmap in-use bits.  The primary page remains pinned and
 * share-locked for the whole walk (see the concurrency notes at the top
 * of the file).
 *
 * Note on duplicate primary pages: given the monotonicity of spares[]
 * verified in hash_check_metapage(), BUCKET_TO_BLKNO is strictly
 * increasing in the bucket number, so two buckets can never share a
 * primary page.  No extra check is needed.
 */
static void
hash_check_bucket(HashCheckState *state, Bucket bucket)
{
	Relation	rel = state->rel;
	BlockNumber primaryblkno;
	BlockNumber blkno;
	BlockNumber prevblkno;
	Buffer		primarybuf;
	Buffer		buffer;
	Page		page;
	HashPageOpaque opaque;
	BlockNumber *visited;
	int			nvisited = 0;
	BlockNumber nblocks;

	/*
	 * Take a fresh metapage snapshot so that BUCKET_TO_BLKNO sees spares[] as
	 * of now (hash_check_ovfl_bitmap saves and restores the snapshot around
	 * its internal refresh).
	 */
	hash_read_meta_copy(state);

	primaryblkno = BUCKET_TO_BLKNO(&state->metacopy, bucket);

	/*
	 * Bucket pages are allocated before the metapage is updated, and this
	 * bucket was already counted in the fresh snapshot, so the primary page
	 * cannot legitimately lie beyond the current end of the index.
	 */
	nblocks = RelationGetNumberOfBlocks(rel);
	if (primaryblkno == InvalidBlockNumber || primaryblkno >= nblocks)
		ereport(ERROR,
				(errcode(ERRCODE_INDEX_CORRUPTED),
				 errmsg("index \"%s\": primary page %u of bucket %u is out of range (relation size %u)",
						RelationGetRelationName(rel),
						primaryblkno, bucket, nblocks)));

	page = hash_read_page_checked(state, primaryblkno, &primarybuf);
	opaque = HashPageGetOpaque(page);

	if ((opaque->hasho_flag & LH_PAGE_TYPE) != LH_BUCKET_PAGE)
		ereport(ERROR,
				(errcode(ERRCODE_INDEX_CORRUPTED),
				 errmsg("index \"%s\": primary page %u of bucket %u is not a bucket page",
						RelationGetRelationName(rel), primaryblkno,
						bucket)));

	if (opaque->hasho_bucket != bucket)
		ereport(ERROR,
				(errcode(ERRCODE_INDEX_CORRUPTED),
				 errmsg("index \"%s\": primary page %u of bucket %u belongs to bucket %u",
						RelationGetRelationName(rel),
						primaryblkno, bucket, opaque->hasho_bucket)));

	hash_check_page_items(state, page, primaryblkno, bucket);

	visited = palloc_array(BlockNumber, Max(nblocks,
											(BlockNumber) MAX_CHAIN_PAGES));
	visited[nvisited++] = primaryblkno;

	/* Walk the chain of overflow pages */
	prevblkno = primaryblkno;
	blkno = opaque->hasho_nextblkno;

	while (BlockNumberIsValid(blkno))
	{
		int			i;

		CHECK_FOR_INTERRUPTS();

		/*
		 * Cycle check: a page may not be visited twice by one walk.  A chain
		 * tail freshly appended by a concurrent insert cannot revisit an
		 * earlier page, so this is corruption, not a race.
		 */
		for (i = 0; i < nvisited; i++)
		{
			if (visited[i] == blkno)
				ereport(ERROR,
						(errcode(ERRCODE_INDEX_CORRUPTED),
						 errmsg("index \"%s\": cycle detected in bucket %u chain at block %u",
								RelationGetRelationName(rel), bucket,
								blkno)));
		}

		/*
		 * The linked block must exist.  A concurrent insert may extend the
		 * index, but the page it links was already allocated when this link
		 * was written, so this cannot mistake a fresh tail for corruption.
		 */
		nblocks = RelationGetNumberOfBlocks(rel);
		if (blkno >= nblocks)
			ereport(ERROR,
					(errcode(ERRCODE_INDEX_CORRUPTED),
					 errmsg("index \"%s\": bucket %u chain references block %u beyond end of relation (size %u)",
							RelationGetRelationName(rel), bucket,
							blkno, nblocks)));

		visited[nvisited++] = blkno;

		page = hash_read_page_checked(state, blkno, &buffer);
		opaque = HashPageGetOpaque(page);

		if ((opaque->hasho_flag & LH_PAGE_TYPE) != LH_OVERFLOW_PAGE)
			ereport(ERROR,
					(errcode(ERRCODE_INDEX_CORRUPTED),
					 errmsg("index \"%s\": bucket %u chain contains non-overflow page %u",
							RelationGetRelationName(rel), bucket,
							blkno),
					 errdetail_internal("Page type flags are 0x%04X.",
										opaque->hasho_flag)));

		if (opaque->hasho_bucket != bucket)
			ereport(ERROR,
					(errcode(ERRCODE_INDEX_CORRUPTED),
					 errmsg("index \"%s\": bucket %u chain contains page %u of bucket %u",
							RelationGetRelationName(rel), bucket,
							blkno, opaque->hasho_bucket)));

		if (opaque->hasho_prevblkno != prevblkno)
			ereport(ERROR,
					(errcode(ERRCODE_INDEX_CORRUPTED),
					 errmsg("index \"%s\": overflow page %u has broken back link %u (expected %u)",
							RelationGetRelationName(rel), blkno,
							opaque->hasho_prevblkno, prevblkno)));

		hash_check_page_items(state, page, blkno, bucket);

		/* The in-use bitmap check must run under the primary lock */
		hash_check_ovfl_bitmap(state, blkno);

		prevblkno = blkno;
		blkno = opaque->hasho_nextblkno;

		UnlockReleaseBuffer(buffer);
	}

	pfree(visited);
	UnlockReleaseBuffer(primarybuf);
}
