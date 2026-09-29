# contrib/pg_backend_msg/Makefile

EXTENSION = pg_backend_msg
DATA = pg_backend_msg--1.0.sql
PGFILEDESC = "pg_backend_msg - pass custom messages to pg_cancel_backend/pg_terminate_backend"

REGRESS = pg_backend_msg

ifdef USE_PGXS
PG_CONFIG = pg_config
PGXS := $(shell $(PG_CONFIG) --pgxs)
include $(PGXS)
else
subdir = contrib/pg_backend_msg
top_builddir = ../..
include $(top_builddir)/src/Makefile.global
include $(top_srcdir)/contrib/contrib-global.mk
endif
