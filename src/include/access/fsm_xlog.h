/*-------------------------------------------------------------------------
 *
 * brin_xlog.h
 *	  POSTGRES FSM XLOG definitions.
 *
 *
 * Portions Copyright (c) 1996-2025, PostgreSQL Global Development Group
 * Portions Copyright (c) 1994, Regents of the University of California
 *
 * src/include/access/fsm_xlog.h
 *
 *-------------------------------------------------------------------------
 */
#ifndef FSM_XLOG_H
#define FSM_XLOG_H


#include "access/xlog.h"
#include "access/xlogdefs.h"
#include "access/xlogreader.h"

#define XLOG_FSM_UPDATE		0x00

/*
 * This is what we need to know about a FSM page update.
 *
 * Backup block 0-31: FSM pages
 */
typedef struct xl_fsm_update
{
    uint32 nchanges;
    
    uint32 ev[FLEXIBLE_ARRAY_MEMBER];
} xl_fsm_update;

#define SizeOfFSMUpdate	(offsetof(xl_fsm_update, nchanges) + \
								 sizeof(int))


extern void fsm_redo(XLogReaderState *record);
extern void fsm_desc(StringInfo buf, XLogReaderState *record);
extern const char *fsm_identify(uint8 info);

#endif							/* FSM_XLOG_H */
