/*-------------------------------------------------------------------------
 *
 * yc_checker.c
 *	  yc routines
 *
 * Portions Copyright (c) 1996-2022, PostgreSQL Global Development Group
 * Portions Copyright (c) 1994, Regents of the University of California
 *
 *
 * IDENTIFICATION
 *	  src/backend/access/common/yc_checker.c
 *
 *-------------------------------------------------------------------------
 */

#include "postgres.h"
#include "access/yc_checker.h"

/* GUC variables */

YCGrantCheckerType yc_grant_checker_type = YC_GRANT_CHECKER_OFF;
