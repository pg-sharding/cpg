/*-------------------------------------------------------------------------
 *
 * fsmdesc.c
 *	  rmgr descriptor routines for storage/freespace/freespace.c
 *
 *
 * Portions Copyright (c) 1996-2025, PostgreSQL Global Development Group
 * Portions Copyright (c) 1994, Regents of the University of California
 *
 * src/backend/access/rmgrdesc/fsmdesc.c
 *
 *-------------------------------------------------------------------------
 */
#include "postgres.h"

#include "access/fsm_xlog.h"
#include "lib/stringinfo.h"


const char *
fsm_identify(uint8 info)
{
	if ((info & ~XLR_INFO_MASK) == XLOG_FSM_UPDATE)
		return "FSM_UPDATE";

	return NULL;
}

void
fsm_desc(StringInfo buf, XLogReaderState *record)
{
	int			i;
	char	   *rec = XLogRecGetData(record);
	uint8		info = XLogRecGetInfo(record) & ~XLR_INFO_MASK;

	if (info == XLOG_FSM_UPDATE)
	{
		xl_fsm_update *xlrec = (xl_fsm_update *) rec;

		appendStringInfo(buf, "nevent: %d ", xlrec->nchanges);

		for (i = 0; i < xlrec->nchanges; ++i)
		{
			appendStringInfo(buf, ", offset %d value %d", xlrec->ev[2 * i], xlrec->ev[2 * i + 1]);
		}
	}
}

