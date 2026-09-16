# contrib/pg_target_promote/meson.build

pg_target_promote_sources = files(
  'pg_target_promote.c',
)

pg_target_promote = shared_module('pg_target_promote',
  pg_target_promote_sources,
  kwargs: contrib_mod_args + {
    'install': true,
  },
)

install_data(
  'pg_target_promote.control',
  'pg_target_promote--1.0.sql',
  kwargs: install_data_args,
)

tests += {
  'name': 'pg_target_promote',
  'sd': meson.current_source_dir(),
  'bd': meson.current_build_dir(),
  'tap': {
    'tests': [
      't/001_bump_timeline.pl',
    ],
  },
}
