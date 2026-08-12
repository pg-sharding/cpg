# contrib/sa_mon/Makefile

MODULE_big = sa_mon
OBJS = \
	$(WIN32RES) \
	sa_mon.o

EXTENSION = sa_mon
DATA = sa_mon--1.0.sql
PGFILEDESC = "sa_mon - shared archive monitoring"

REGRESS = sa_mon
TAP_TESTS = 1

ifdef USE_PGXS
PG_CONFIG = pg_config
PGXS := $(shell $(PG_CONFIG) --pgxs)
include $(PGXS)
else
subdir = contrib/sa_mon
top_builddir = ../..
include $(top_builddir)/src/Makefile.global
include $(top_srcdir)/contrib/contrib-global.mk
endif
