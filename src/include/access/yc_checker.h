#
/*-------------------------------------------------------------------------
 *
 * yc_checker.h
 *
 *  Header file for YC MDB specific only GUC variables, 
 *
 * Portions Copyright (c) 1996-2021, PostgreSQL Global Development Group
 * Portions Copyright (c) 1994, Regents of the University of California
 *
 * src/include/storage/yc_checker.h
 *
 *-------------------------------------------------------------------------
 */
#ifndef PG_YC_CHECKER_H
#define PG_YC_CHECKER_H

/* Possible values for yc_grant_checker_type */
typedef enum
{
	YC_GRANT_CHECKER_OFF,
	YC_GRANT_CHECKER_WARN,
	YC_GRANT_CHECKER_CRIT,
} YCGrantCheckerType;

/* GUC variables */

extern PGDLLIMPORT YCGrantCheckerType yc_grant_checker_type;


#endif /* PG_YC_CHECKER_H */
