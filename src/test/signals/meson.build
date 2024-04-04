# Copyright (c) 2024-2024, PostgreSQL Global Development Group

tests += {
  'name': 'signals',
  'sd': meson.current_source_dir(),
  'bd': meson.current_build_dir(),
  'tap': {
    'env': {
       'enable_injection_points': get_option('injection_points') ? 'yes' : 'no',
    },
    'tests': [
      't/001_signal_autovacuum.pl',
    ],
  },
}
