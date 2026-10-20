# Copyright (c) 2025-2025, PostgreSQL Global Development Group

pg_target_promote_sources = files(
  'pg_target_promote.c',
)

if host_system == 'windows'
  pg_target_promote_sources += rc_lib_gen.process(win32ver_rc, extra_args: [
    '--NAME', 'pg_target_promote',
    '--FILEDESC', 'pg_target_promote - promote standby to a target timeline',])
endif

pg_target_promote = shared_module('pg_target_promote',
  pg_target_promote_sources,
  kwargs: contrib_mod_args,
)
contrib_targets += pg_target_promote

install_data(
  'pg_target_promote--1.0.sql',
  'pg_target_promote.control',
  kwargs: contrib_data_args,
)
