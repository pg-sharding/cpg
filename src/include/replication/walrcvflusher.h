/*-------------------------------------------------------------------------
 *
 * walrcvflusher.h
 *	  Exports from replication/walrcvflusher.c.
 *
 * Portions Copyright (c) 2010-2025, PostgreSQL Global Development Group
 *
 * src/include/replication/walrcvflusher.h
 *
 *-------------------------------------------------------------------------
 */
#ifndef _WALRCVFLUSHER_H
#define _WALRCVFLUSHER_H

extern void WalRcvFlusherMain(char *startup_data, 
										size_t startup_data_len) pg_attribute_noreturn();
extern void WakeupWalRcvFlusher(void);

#endif							/* _WALRCVFLUSHER_H */
