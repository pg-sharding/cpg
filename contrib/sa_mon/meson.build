# Copyright (c) 2025, PostgreSQL Global Development Group

sa_mon_sources = files(
  'sa_mon.c',
)

if host_system == 'windows'
  sa_mon_sources += rc_lib_gen.process(win32ver_rc, extra_args: [
    '--NAME', 'sa_mon',
    '--FILEDESC', 'sa_mon - shared archive monitoring',])
endif

sa_mon = shared_module('sa_mon',
  sa_mon_sources,
  kwargs: contrib_mod_args,
)
contrib_targets += sa_mon

install_data(
  'sa_mon.control',
  'sa_mon--1.0.sql',
  kwargs: contrib_data_args,
)

tests += {
  'name': 'sa_mon',
  'sd': meson.current_source_dir(),
  'bd': meson.current_build_dir(),
  'regress': {
    'sql': [
      'sa_mon',
    ],
  },
  'tap': {
    'tests': [
      't/001_mdb_get_sa_info.pl',
    ],
  },
}
