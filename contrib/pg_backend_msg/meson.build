# Copyright (c) 2026, PostgreSQL Global Development Group

install_data(
  'pg_backend_msg.control',
  'pg_backend_msg--1.0.sql',
  kwargs: contrib_data_args,
)

tests += {
  'name': 'pg_backend_msg',
  'sd': meson.current_source_dir(),
  'bd': meson.current_build_dir(),
  'regress': {
    'sql': [
      'pg_backend_msg',
    ],
    'regress_args': [
    ],
  },
}
