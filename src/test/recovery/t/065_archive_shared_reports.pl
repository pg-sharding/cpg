# Copyright (c) 2026, PostgreSQL Global Development Group

# Reports must work independently of keepalives.  Ordinary physical clients
# must not receive the opt-in protocol messages.
use strict;
use warnings FATAL => 'all';
use PostgreSQL::Test::Cluster;
use PostgreSQL::Test::Utils;
use Test::More;

my $archive = PostgreSQL::Test::Utils::tempdir();
my $copy = $PostgreSQL::Test::Utils::windows_os
  ? qq{copy "%p" "$archive\\%f"}
  : qq{cp "%p" "$archive/%f"};
my $a = PostgreSQL::Test::Cluster->new('primary');
$a->init(allows_streaming => 1, extra => ['--wal-segsize' => 1]);
$a->append_conf(
	'postgresql.conf', qq(
archive_mode = on
archive_command = '$copy'
wal_sender_timeout = 0
wal_keep_size = '64MB'
));
$a->start;
$a->backup('backup');

my $b = PostgreSQL::Test::Cluster->new('standby');
$b->init_from_backup($a, 'backup', has_streaming => 1);
$b->append_conf(
	'postgresql.conf', qq(
archive_mode = shared
archive_status_report_interval = '100ms'
archive_command = ''
wal_receiver_status_interval = 0
wal_receiver_timeout = 0
hot_standby_feedback = off
));
$b->start;
$a->wait_for_catchup($b);
my $old = $a->safe_psql('postgres',
	'SELECT pg_walfile_name(pg_current_wal_lsn())');
$a->safe_psql('postgres', 'SELECT txid_current(); SELECT pg_switch_wal()');
$a->poll_query_until('postgres',
	"SELECT last_archived_wal >= '$old' FROM pg_stat_archiver")
  or die 'primary did not archive the test segment';
$a->wait_for_catchup($b);

# With timeout-driven and periodic receiver messages disabled, an idle sender
# must still wake for the archive-report deadline.
$b->poll_query_until('postgres',
	"SELECT primary_last_archived >= '$old' FROM pg_stat_wal_receiver")
  or die 'archive report did not arrive with wal_sender_timeout=0';
pass('archive reports arrive with keepalive timeouts disabled');

$a->safe_psql('postgres',
	q{ALTER SYSTEM SET wal_sender_timeout = '5s'; SELECT pg_reload_conf()});
$old = $a->safe_psql('postgres',
	'SELECT pg_walfile_name(pg_current_wal_lsn())');
$a->safe_psql('postgres', 'SELECT txid_current(); SELECT pg_switch_wal()');
$b->poll_query_until('postgres',
	"SELECT primary_last_archived >= '$old' FROM pg_stat_wal_receiver")
  or die 'positive-timeout control received no report';
pass('reports also arrive with a positive sender timeout');

# Clients without an explicit request must work even with permanent slots.
$a->safe_psql('postgres',
	q{SELECT * FROM pg_create_physical_replication_slot('backup_slot', true)});
my $backup = PostgreSQL::Test::Utils::tempdir() . '/backup';
command_ok(
	[
		'pg_basebackup', '-D', $backup, '-d', $a->connstr,
		'-X', 'stream', '-S', 'backup_slot', '-c', 'fast'
	],
	'pg_basebackup with a permanent slot receives no unsolicited reports');

$a->safe_psql('postgres',
	q{SELECT * FROM pg_create_physical_replication_slot('receive_slot', true);
      SELECT txid_current()});
my $end = $a->safe_psql('postgres', 'SELECT pg_switch_wal()');
my $dest = PostgreSQL::Test::Utils::tempdir();
command_ok(
	[
		'pg_receivewal', '-D', $dest, '-d', $a->connstr,
		'-S', 'receive_slot', '--no-loop', '--endpos=' . $end
	],
	'pg_receivewal with a permanent slot streams through its endpoint');
$b->stop;
$a->stop;
done_testing();
