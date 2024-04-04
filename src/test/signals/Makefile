#-------------------------------------------------------------------------
#
# Makefile for src/test/signals
#
# Portions Copyright (c) 1996-2024, PostgreSQL Global Development Group
# Portions Copyright (c) 1994, Regents of the University of California
#
# src/test/signals/Makefile
#
#-------------------------------------------------------------------------

EXTRA_INSTALL=src/test/modules/injection_points

subdir = src/test/signals
top_builddir = ../../..
include $(top_builddir)/src/Makefile.global

export enable_injection_points enable_injection_points

check:
	$(prove_check)

installcheck:
	$(prove_installcheck)

clean distclean maintainer-clean:
	rm -rf tmp_check
