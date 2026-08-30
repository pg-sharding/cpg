# contrib/pg_target_promote/Makefile

MODULE_big	= pg_target_promote
OBJS = \
	$(WIN32RES) \
	pg_target_promote.o

EXTENSION = pg_target_promote
DATA = pg_target_promote--1.0.sql
PGFILEDESC = "pg_target_promote - promote standby to a target timeline"

ifdef USE_PGXS
PG_CONFIG = pg_config
PGXS := $(shell $(PG_CONFIG) --pgxs)
include $(PGXS)
else
subdir = contrib/pg_target_promote
top_builddir = ../..
include $(top_builddir)/src/Makefile.global
include $(top_srcdir)/contrib/contrib-global.mk
endif
