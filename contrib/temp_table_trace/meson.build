# Copyright (c) 2025, PostgreSQL Global Development Group

temp_table_trace_sources = files(
  'temp_table_trace.c',
)

if host_system == 'windows'
  temp_table_trace_sources += rc_lib_gen.process(win32ver_rc, extra_args: [
    '--NAME', 'temp_table_trace',
    '--FILEDESC', 'temp_table_trace - trace temporary relation lifecycle (skeleton)',])
endif

temp_table_trace = shared_module('temp_table_trace',
  temp_table_trace_sources,
  kwargs: contrib_mod_args,
)
contrib_targets += temp_table_trace
