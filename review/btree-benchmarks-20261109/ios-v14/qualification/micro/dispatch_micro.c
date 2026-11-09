/* Actual-returnitem and actual-tableAM-helper kernels. No AM/VM/heap claim. */
#include "postgres.h"
#include "fmgr.h"
#include "access/nbtree.h"
#include "access/tableam_indexscan.h"
#include "catalog/pg_type_d.h"
#include "utils/builtins.h"
#include "utils/memutils.h"

PG_MODULE_MAGIC;
PG_FUNCTION_INFO_V1(ios_dispatch_micro);
PG_FUNCTION_INFO_V1(ios_dispatch_oracle);

/* This header is extracted byte-for-byte from the matching nbtsearch.c. */
#include "returnitem-body.h"

static pg_noinline void
dispatch_actual(IndexScanDesc scan, BTScanOpaque so)
{
	_bt_returnitem(scan, so);
}

static pg_noinline void
fill_actual(IndexScanDesc scan, TupleTableSlot *slot)
{
	tableam_index_fill_ios_slot(scan, slot);
	/* All roles retain the real call/return cost of the production caller. */
	__asm__ __volatile__("" ::: "memory");
}

typedef struct Kernel
{
	IndexScanDescData scan;
	BTScanOpaque so;
	TupleDesc desc;
	TupleTableSlot *slot;
	int nitems;
	int repeat;
	int singles;
	bool text;
} Kernel;

static void
reset_page(Kernel *k)
{
#ifdef MICRO_PAGE_CACHE
	k->so->iosCache.itup = NULL;
	k->scan.xs_itupcache = k->so->currPos.hasPosting ? &k->so->iosCache : NULL;
#elif defined(MICRO_WITH_CACHE)
	k->so->iosTupleOffset = -1;
	k->so->iosCache.valid = false;
	k->scan.xs_itupcache = NULL;
#endif
}

/* repeat>=2, singles>0 produces sparse posting groups on the SAME page. */
static void
setup(Kernel *k, int natts, int repeat, int singles, bool text, bool nulls)
{
	Datum values[INDEX_MAX_KEYS];
	bool isnull[INDEX_MAX_KEYS];
	IndexTuple tuple;
	Size size;
	int offset = 0;
	int nitems = 0;
	int tuple_no = 0;

	MemSet(k,0,sizeof(*k));
	k->repeat=repeat; k->singles=singles; k->text=text;
	k->desc=CreateTemplateTupleDesc(natts);
	for(int i=0;i<natts;i++)
	{
		TupleDescInitEntry(k->desc,i+1,NULL,text?TEXTOID:INT4OID,-1,0);
		values[i]=text?CStringGetTextDatum("short-test-value"):Int32GetDatum(100+i);
		isnull[i]=nulls && i%4==1;
	}
	TupleDescFinalize(k->desc);
	tuple=index_form_tuple(k->desc,values,isnull);
	size=MAXALIGN(IndexTupleSize(tuple));
	/* Very wide tuples cannot fit 32 singletons on one physical page. */
	singles=Min(singles,(int)(BLCKSZ/size)-1);
	k->singles=singles;
	k->so=palloc0(sizeof(BTScanOpaqueData));
	k->so->currTuples=palloc0(BLCKSZ*2+natts*(sizeof(Datum)+sizeof(bool)));
	k->so->markTuples=k->so->currTuples+BLCKSZ;
#ifdef MICRO_WITH_CACHE
	if(natts>1)
	{
		k->so->iosCache.values=(Datum*)(k->so->currTuples+BLCKSZ*2);
		k->so->iosCache.isnull=(bool*)(k->so->iosCache.values+natts);
	}
	k->so->currPos.hasPosting=repeat>1 && natts>1;
#ifdef MICRO_PAGE_CACHE
	k->so->iosCache.required_flags=INDEX_ALT_TID_MASK;
#ifdef MICRO_CACHED_NATTS
	k->so->iosCache.natts=natts;
#endif
#endif
#endif
	/* Repeat a posting group then `singles` distinct singleton tuples. */
	while(offset+(singles+1)*size<=BLCKSZ &&
		  nitems+repeat+singles<=MaxTIDsPerBTreePage)
	{
		for(int group=0;group<=singles;group++)
		{
			int count=group==0?repeat:1;
			IndexTuple distinct;
			Datum first=values[0];
			values[0]=text?CStringGetTextDatum(psprintf("tuple-%08d",tuple_no)):
				Int32GetDatum(100+tuple_no);
			distinct=index_form_tuple(k->desc,values,isnull);
#ifdef MICRO_PAGE_CACHE
			/* Same preserved header as a saved posting base, no TID array. */
			if(count>1)
				BTreeTupleSetPosting(distinct,count,MAXALIGN(IndexTupleSize(distinct)));
#endif
			Assert(IndexTupleSize(distinct)<=size);
			memcpy(k->so->currTuples+offset,distinct,IndexTupleSize(distinct));
			if(text)pfree(DatumGetPointer(values[0]));
			values[0]=first;
			pfree(distinct);
			for(int j=0;j<count;j++)
			{
				BTScanPosItem *item=&k->so->currPos.items[nitems];
				ItemPointerSet(&item->heapTid,0,nitems+1);
				item->indexOffset=tuple_no+1;
				item->tupleOffset=offset;
				nitems++;
			}
			offset+=size;
			tuple_no++;
		}
	}
	Assert(nitems>0);
	k->nitems=nitems;
	k->so->currPos.currPage=0;
	k->so->currPos.buf=InvalidBuffer;
	k->so->currPos.firstItem=0;
	k->so->currPos.lastItem=nitems-1;
	k->scan.opaque=k->so;
	k->scan.xs_itupdesc=k->desc;
	k->slot=MakeSingleTupleTableSlot(k->desc,&TTSOpsVirtual);
	reset_page(k);
	pfree(tuple);
}

static void
finish(Kernel *k)
{
	ExecDropSingleTupleTableSlot(k->slot);
	pfree(k->so->currTuples);
	pfree(k->so);
	FreeTupleDesc(k->desc);
}

/* natts,loops,repeat,singles,TEXT,NULL,fill,reverse,visible_stride */
Datum
ios_dispatch_micro(PG_FUNCTION_ARGS)
{
	int natts=PG_GETARG_INT32(0);
	int64 loops=PG_GETARG_INT64(1);
	int repeat=PG_GETARG_INT32(2);
	int singles=PG_GETARG_INT32(3);
	bool text=PG_GETARG_BOOL(4);
	bool nulls=PG_GETARG_BOOL(5);
	bool fill=PG_GETARG_BOOL(6);
	bool reverse=PG_GETARG_BOOL(7);
	int stride=PG_GETARG_INT32(8);
	Kernel k;
	uint64 checksum=0;
	int pos;
	int remaining=0;

	if(natts<1 || natts>INDEX_MAX_KEYS || loops<1 || loops>100000000 ||
	   repeat<1 || repeat>64 || singles<0 || singles>32 || stride<1 || stride>64)
		elog(ERROR,"invalid dispatch kernel dimensions");
	setup(&k,natts,repeat,singles,text,nulls);
	pos=reverse?k.nitems-1:0;
	for(int64 i=0;i<loops;i++)
	{
		k.so->currPos.itemIndex=pos;
		dispatch_actual(&k.scan,k.so);
		if(fill && remaining==0)
		{
			fill_actual(&k.scan,k.slot);
			checksum+=text?VARSIZE_ANY_EXHDR(DatumGetPointer(k.slot->tts_values[0])):
				DatumGetInt32(k.slot->tts_values[0]);
			remaining=stride;
		}
		if(fill)remaining--;
		checksum+=ItemPointerGetOffsetNumber(&k.scan.xs_heaptid);
		/* Observable loop index and output; baseline bookkeeping is retained. */
		asm volatile("" : : "r"(i),"r"(k.scan.xs_itup),"r"(checksum),"r"(remaining) : "memory");
		pos+=reverse?-1:1;
		if(pos<0 || pos>=k.nitems)
		{
			pos=reverse?k.nitems-1:0;
			reset_page(&k);
		}
	}
	finish(&k);
	PG_RETURN_INT64((int64)checksum);
}

/* Random jumps/reversals, sparse visible consumption, resets, exact values. */
Datum
ios_dispatch_oracle(PG_FUNCTION_ARGS)
{
	uint64 checks=0;
	for(int natts=1;natts<=32;natts=natts==1?2:natts==2?4:natts==4?8:natts==8?32:33)
	for(int rep=1;rep<=64;rep=rep==1?2:rep==2?64:65)
	for(int singles=0;singles<=32;singles=singles==0?1:singles==1?8:singles==8?32:33)
	{
		Kernel k;
		uint32 random=20261107;
		Datum expected[INDEX_MAX_KEYS];
		bool nulls[INDEX_MAX_KEYS];
		setup(&k,natts,rep,singles,true,true);
		for(int i=0;i<2000;i++)
		{
			int pos;
			random=random*1664525+1013904223;
			pos=random%k.nitems;
			if(i%47==0)reset_page(&k);
			k.so->currPos.itemIndex=pos;
#ifdef MICRO_PAGE_CACHE
			IndexTuple previous_key=k.so->iosCache.itup;
#endif
			dispatch_actual(&k.scan,k.so);
#ifdef MICRO_PAGE_CACHE
			if(k.so->iosCache.itup!=previous_key)
				elog(ERROR,"returnitem unexpectedly modified cache metadata");
#endif
			if(k.scan.xs_itup!=(IndexTuple)(k.so->currTuples+k.so->currPos.items[pos].tupleOffset) ||
			   !ItemPointerEquals(&k.scan.xs_heaptid,&k.so->currPos.items[pos].heapTid))
				elog(ERROR,"returnitem identity mismatch");
#ifdef MICRO_WITH_CACHE
			{
				bool reusable=natts>1 && rep>1 &&
					((pos>0 && k.so->currPos.items[pos-1].tupleOffset==k.so->currPos.items[pos].tupleOffset)||
					 (pos+1<k.nitems && k.so->currPos.items[pos+1].tupleOffset==k.so->currPos.items[pos].tupleOffset));
#ifdef MICRO_PAGE_CACHE
				if((k.scan.xs_itupcache!=NULL)!=k.so->currPos.hasPosting ||
				   reusable!=((k.scan.xs_itup->t_info & INDEX_ALT_TID_MASK)!=0 && natts>1))
					elog(ERROR,"page attachment/flag mismatch at %d/%d/%d",natts,rep,singles);
#else
				if((k.scan.xs_itupcache!=NULL)!=reusable)
					elog(ERROR,"reuse attachment mismatch at %d/%d/%d",natts,rep,singles);
#endif
			}
#endif
			/* Not every returned TID reaches deformation (visibility rejection). */
			if(i%3!=0)
			{
				index_deform_tuple(k.scan.xs_itup,k.desc,expected,nulls);
				fill_actual(&k.scan,k.slot);
#ifdef MICRO_PAGE_CACHE
				if(k.scan.xs_itupcache!=NULL &&
				   k.so->iosCache.itup!=((k.scan.xs_itup->t_info & INDEX_ALT_TID_MASK)!=0 ? k.scan.xs_itup : previous_key))
					elog(ERROR,"visible consume cache key mismatch");
#endif
				for(int j=0;j<natts;j++)
				{
					if(k.slot->tts_isnull[j]!=nulls[j] ||
					   (!nulls[j] && memcmp(DatumGetPointer(k.slot->tts_values[j]),DatumGetPointer(expected[j]),VARSIZE_ANY(DatumGetPointer(expected[j])))!=0))
						elog(ERROR,"slot value mismatch");
					checks++;
				}
			}
		}
		finish(&k);
	}
	PG_RETURN_INT64((int64)checks);
}

PG_FUNCTION_INFO_V1(ios_pagecache_oracle);

/* Additional v8 contract oracle, not an invocation of _bt_readpage/restore. */
Datum
ios_pagecache_oracle(PG_FUNCTION_ARGS)
{
#ifdef MICRO_PAGE_CACHE
	Kernel k;
	uint64 checks=0;
	setup(&k,4,2,1,false,true);
	for(int i=0;i<128;i++)
	{
		IndexTuple posting=(IndexTuple)k.so->currTuples;
		int32 value=1000+i;

		/* Invalidate BEFORE replacing bytes at an unchanged workspace address. */
		reset_page(&k);
		memcpy((char*)posting+IndexInfoFindDataOffset(posting->t_info),&value,sizeof(value));
		k.so->currPos.itemIndex=0;
		dispatch_actual(&k.scan,k.so);
		fill_actual(&k.scan,k.slot);
		if(k.so->iosCache.itup!=posting || DatumGetInt32(k.slot->tts_values[0])!=value || !k.slot->tts_isnull[1])
			elog(ERROR,"same-address page replacement mismatch");
		checks++;

		/* A visible singleton bypasses and preserves this posting cache. */
		k.so->currPos.itemIndex=2;
		dispatch_actual(&k.scan,k.so);
		fill_actual(&k.scan,k.slot);
		if(k.so->iosCache.itup!=posting || DatumGetInt32(k.slot->tts_values[0])!=101)
			elog(ERROR,"singleton did not preserve last posting cache");
		checks++;

		/* Returning backwards to the same posting must recover exact values. */
		k.so->currPos.itemIndex=1;
		dispatch_actual(&k.scan,k.so);
		fill_actual(&k.scan,k.slot);
		if(k.so->iosCache.itup!=posting || DatumGetInt32(k.slot->tts_values[0])!=value)
			elog(ERROR,"posting/singleton/posting mismatch");
		checks++;

		/* Legal eligibility mutation at the SAME address: reset before write. */
		reset_page(&k);
		posting->t_info &= ~INDEX_ALT_TID_MASK;
		value += 10000;
		memcpy((char*)posting+IndexInfoFindDataOffset(posting->t_info),&value,sizeof(value));
		k.so->currPos.itemIndex=0;
		dispatch_actual(&k.scan,k.so);
		fill_actual(&k.scan,k.slot);
		if(k.so->iosCache.itup!=NULL || DatumGetInt32(k.slot->tts_values[0])!=value)
			elog(ERROR,"reset before eligibility change mismatch");
		checks++;

		/* Reset before changing the AM qualification mask, too. */
		reset_page(&k);
		posting->t_info |= INDEX_ALT_TID_MASK;
		if(posting->t_info & INDEX_VAR_MASK)
			elog(ERROR,"expected fixed-width contract fixture");
		k.so->iosCache.required_flags=INDEX_ALT_TID_MASK | INDEX_VAR_MASK;
		fill_actual(&k.scan,k.slot);
		if(k.so->iosCache.itup!=NULL || DatumGetInt32(k.slot->tts_values[0])!=value)
			elog(ERROR,"reset before mask change mismatch");
		checks++;
		reset_page(&k);
		k.so->iosCache.required_flags=INDEX_ALT_TID_MASK;
	}
	finish(&k);
	PG_RETURN_INT64((int64)checks);
#else
	PG_RETURN_INT64(0);
#endif
}
