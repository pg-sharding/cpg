# Copyright (c) 2026, PostgreSQL Global Development Group

# Test that mdb_get_sa_info() reports the last WAL segment archived by the
# primary, as received by a standby running with archive_mode=shared.
use strict;
use warnings FATAL => 'all';
use PostgreSQL::Test::Cluster;
use PostgreSQL::Test::Utils;
use Test::More;

my $archive_dir = PostgreSQL::Test::Utils::tempdir();
my $archive_command =
  $PostgreSQL::Test::Utils::windows_os
  ? qq{copy "%p" "$archive_dir\\%f"}
  : qq{cp "%p" "$archive_dir/%f"};

my $primary = PostgreSQL::Test::Cluster->new('primary');
$primary->init(has_archiving => 1, allows_streaming => 1);
$primary->append_conf(
	'postgresql.conf', qq{
archive_mode = shared
archive_command = '$archive_command'
ycmdb.archive_status_report_interval = 10ms
wal_keep_size = 128MB
});
$primary->start;

$primary->safe_psql('postgres', 'CREATE EXTENSION sa_mon');

# A primary never receives archival reports, so nothing is stored.
is($primary->safe_psql('postgres', 'SELECT mdb_get_sa_info() IS NULL'),
	't', 'mdb_get_sa_info() returns NULL on a primary');

my $backup_name = 'standby_backup';
$primary->backup($backup_name);

my $standby = PostgreSQL::Test::Cluster->new('standby');
$standby->init_from_backup($primary, $backup_name, has_streaming => 1);
$standby->append_conf(
	'postgresql.conf', qq{
archive_mode = shared
archive_command = '$archive_command'
ycmdb.archive_status_report_interval = 10ms
wal_receiver_status_interval = 1s
});
$standby->start;

$primary->wait_for_catchup($standby);

# Archive a segment on the primary, so that it has something to report.
my $archived_before = $primary->safe_psql('postgres',
	'SELECT archived_count FROM pg_stat_archiver');
$primary->safe_psql('postgres',
	'SELECT txid_current(); SELECT pg_switch_wal();');
$primary->poll_query_until('postgres',
	"SELECT archived_count > $archived_before FROM pg_stat_archiver")
  or die "timed out waiting for the primary to archive a segment";

$primary->wait_for_catchup($standby);

# The standby learns about it through the replication protocol.
$standby->poll_query_until('postgres', 'SELECT mdb_get_sa_info() IS NOT NULL')
  or die "timed out waiting for an archival report on the standby";

my $last_archived = $primary->safe_psql('postgres',
	'SELECT last_archived_wal FROM pg_stat_archiver');
$standby->poll_query_until('postgres',
	"SELECT mdb_get_sa_info() = '$last_archived'")
  or die "timed out waiting for mdb_get_sa_info() to match the primary";

is($standby->safe_psql('postgres', 'SELECT mdb_get_sa_info()'),
	$last_archived,
	'mdb_get_sa_info() reports the last segment archived by the primary');

done_testing();
