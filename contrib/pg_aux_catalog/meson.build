# Copyright (c) 2022-2025, PostgreSQL Global Development Group

pg_aux_catalog_sources = files(
  'pg_aux_catalog.c',
)

if host_system == 'windows'
  pg_aux_catalog_sources += rc_lib_gen.process(win32ver_rc, extra_args: [
    '--NAME', 'pg_aux_catalog',
    '--FILEDESC', 'pg_aux_catalog - auxiliary catalog management',])
endif

pg_aux_catalog = shared_module('pg_aux_catalog',
  pg_aux_catalog_sources,
  kwargs: contrib_mod_args,
)
contrib_targets += pg_aux_catalog

install_data(
  'pg_aux_catalog--1.0.sql',
  install_dir: contrib_data_dir,
)