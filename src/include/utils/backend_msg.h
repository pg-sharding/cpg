/*-------------------------------------------------------------------------
 *
 * backend_msg.h
 *		Declarations for backend_msg.c
 *
 * Portions Copyright (c) 1996-2026, PostgreSQL Global Development Group
 * Portions Copyright (c) 1994, Regents of the University of California
 *
 * src/include/utils/backend_msg.h
 *
 *-------------------------------------------------------------------------
 */
#ifndef BACKEND_MSG_H
#define BACKEND_MSG_H

#include "storage/proc.h"
#include "storage/shmem.h"

#define BACKEND_MSG_MAX_LEN 128

extern void BackendMsgInit(int id);
extern int BackendMsgSet(ProcNumber procno, const char *msg);
extern int BackendMsgGet(char *buf, int max_len);
extern bool BackendMsgIsSet(void);

#endif							/* BACKEND_MSG_H */
