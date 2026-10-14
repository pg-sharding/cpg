
# Copyright (c) 2026, PostgreSQL Global Development Group

# Test ycmdb.cascade_feedback_quorum: when enabled, a standby reports the
# minimum of its own write/flush/apply LSNs and those of its cascaded
# standbys to the upstream primary.

use strict;
use warnings FATAL => 'all';
use PostgreSQL::Test::Cluster;
use PostgreSQL::Test::Utils;
use Test::More;

# Primary
my $primary = PostgreSQL::Test::Cluster->new('primary');
$primary->init(allows_streaming => 1);
$primary->start;

# Standby of the primary, with cascade feedback enabled
my $standby = PostgreSQL::Test::Cluster->new('standby');
$primary->backup('bkp');
$standby->init_from_backup($primary, 'bkp', has_streaming => 1);
$standby->append_conf(
	'postgresql.conf', qq(
ycmdb.cascade_feedback_quorum = on
wal_receiver_status_interval = 1s
));
$standby->start;

# Cascaded standby of the standby
my $cascade = PostgreSQL::Test::Cluster->new('cascade');
$cascade->init_from_backup($primary, 'bkp', has_streaming => 1);
# point it at the standby rather than the primary
my $connstr = $standby->connstr . " application_name=cascade";
$cascade->append_conf('postgresql.conf',
	qq(primary_conninfo = '$connstr'));
$cascade->append_conf('postgresql.conf', qq(wal_receiver_status_interval = 1s));
$cascade->start;

# Initial WAL, let both standbys catch up
$primary->safe_psql('postgres', "CREATE TABLE feedback_tab (a int)");
$primary->safe_psql('postgres', "INSERT INTO feedback_tab VALUES (1)");
my $lsn1 = $primary->safe_psql('postgres',
	"SELECT pg_current_wal_insert_lsn()");

$primary->wait_for_catchup('standby', 'replay', $lsn1);
$standby->wait_for_catchup('cascade', 'replay', $lsn1);

# Pause replay on the cascaded standby, so it will lag behind.  Wait a bit
# so that its last feedback (write/flush/apply == $lsn1) reaches the
# standby's walsender before it stops.
$cascade->safe_psql('postgres', "SELECT pg_wal_replay_pause()");
is($cascade->safe_psql('postgres', "SELECT pg_get_wal_replay_pause_state()"),
	'paused', 'cascaded standby replay paused');
my $cascade_lsn = $cascade->safe_psql('postgres',
	'SELECT pg_last_wal_replay_lsn()');
ok($standby->poll_query_until(
	'postgres',
	qq[SELECT replay_lsn = '$cascade_lsn' FROM pg_stat_replication
		WHERE application_name = 'cascade'],
	't'),
	'standby knows the cascaded standby position');

# Generate WAL that reaches the standby, but not the cascaded standby
$primary->safe_psql('postgres', "INSERT INTO feedback_tab VALUES (2)");
my $lsn2 = $primary->safe_psql('postgres',
	"SELECT pg_current_wal_insert_lsn()");
# the standby's *replay* feedback now stays at the cascaded standby's
# position, so wait for flush instead
$primary->wait_for_catchup('standby', 'flush', $lsn2);

# The primary must be told about the minimum: the cascaded standby's
# position, not the standby's own position.
ok($primary->poll_query_until(
	'postgres',
	qq[SELECT replay_lsn = '$cascade_lsn' FROM pg_stat_replication
		WHERE application_name = 'standby'],
	't'),
	'primary receives minimum LSN of standby and cascaded standby');
isnt($cascade_lsn,
	$standby->safe_psql('postgres', 'SELECT pg_last_wal_replay_lsn()'),
	'standby itself is ahead of cascaded standby');

done_testing();
