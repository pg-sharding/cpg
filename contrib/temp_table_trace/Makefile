# contrib/temp_table_trace/Makefile

MODULES = temp_table_trace
PGFILEDESC = "temp_table_trace - trace temporary relation lifecycle (skeleton)"

REGRESS = temp_table_trace

ifdef USE_PGXS
PG_CONFIG = pg_config
PGXS := $(shell $(PG_CONFIG) --pgxs)
include $(PGXS)
else
subdir = contrib/temp_table_trace
top_builddir = ../..
include $(top_builddir)/src/Makefile.global
include $(top_srcdir)/contrib/contrib-global.mk
endif
