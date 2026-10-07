# MDB-48544: physical WAL streaming (slotless or with a physical slot)
# requires the REPLICATION attribute; mdb_replication members are only
# allowed on the logical path.  Permission checks key off the
# session-cached globals set in the postinit.c transactional start block
# (role_has_rolreplication, member_of_mdb_replication); no uncached
# superuser()/syscache lookup may run in the walsender startup path.
#
# When a START_REPLICATION command is accepted the server switches to
# copy-both mode; plain psql then reports "unexpected PQresultStatus: 8"
# on stderr and exits.  That psql diagnostic is the marker used below to
# tell "replication actually started" apart from permission errors.

use strict;
use warnings FATAL => 'all';

use PostgreSQL::Test::Cluster;
use PostgreSQL::Test::Utils;
use Test::More;

my $node = PostgreSQL::Test::Cluster->new('primary');
$node->init(allows_streaming => 'physical');
$node->append_conf('postgresql.conf', "wal_level = logical\n");
$node->start;

$node->safe_psql(
	'postgres', qq[
	CREATE ROLE mdb_replication NOLOGIN;
	CREATE ROLE r_repl LOGIN REPLICATION;
	CREATE ROLE r_mdb LOGIN;
	CREATE ROLE r_plain LOGIN;
	GRANT mdb_replication TO r_mdb;
]);

$node->safe_psql(
	'postgres',
	q[SELECT pg_create_physical_replication_slot('s1', true)]);

# Run one replication-protocol command over a walsender connection as the
# given role.  A physical walsender connection (replication=true) is used
# by default; pass db => 1 for a database walsender connection
# (replication=database), which logical decoding commands require.
# Returns ($ret, $stdout, $stderr).
sub walsender_psql
{
	my ($role, $cmd, %opts) = @_;
	my $stdout = '';
	my $stderr = '';
	my $ret = $node->psql(
		'postgres', $cmd,
		replication => ($opts{db} ? 'database' : 'true'),
		extra_params => [ '-U', $role ],
		stdout => \$stdout,
		stderr => \$stderr,
		on_error_die => 0,
		on_error_stop => 1);
	return ($ret, $stdout, $stderr);
}

my $perm_err = qr/must be superuser or replication role/;

# psql's diagnostic upon entering copy-both mode (accepted
# START_REPLICATION, i.e. replication actually started).
my $stream_started = qr/unexpected PQresultStatus: 8/;

my ($ret, $out, $err);

# a) plain role cannot even start a WAL sender
(undef, undef, $err) = walsender_psql('r_plain', 'IDENTIFY_SYSTEM');
like($err, qr/permission denied to start WAL sender/,
	'plain role refused at walsender start');

# b) REPLICATION role may stream physically, slotless and with a slot
($ret, $out, $err) = walsender_psql('r_repl', 'START_REPLICATION 0/0 TIMELINE 1');
like($err, $stream_started, 'REPLICATION role streams slotless (copy-both)');
unlike($err, $perm_err, 'no permission error for slotless REPLICATION streaming');

($ret, $out, $err) =
  walsender_psql('r_repl', 'START_REPLICATION SLOT "s1" 0/0 TIMELINE 1');
like($err, $stream_started, 'REPLICATION role streams from a slot (copy-both)');
unlike($err, $perm_err, 'no permission error for slot REPLICATION streaming');

# c) mdb_replication member cannot stream physically, neither slotless...
($ret, $out, $err) = walsender_psql('r_mdb', 'START_REPLICATION 0/0 TIMELINE 1');
isnt($ret, 0, 'mdb_replication member cannot stream slotless (fails)');
like($err, $perm_err,
	'mdb_replication member cannot stream slotless (physical)');

# ...nor with a physical slot...
($ret, $out, $err) =
  walsender_psql('r_mdb', 'START_REPLICATION SLOT "s1" 0/0 TIMELINE 1');
isnt($ret, 0, 'mdb_replication member cannot stream from a physical slot (fails)');
like($err, $perm_err,
	'mdb_replication member cannot stream from a physical slot');

# ...nor create physical slots
($ret, $out, $err) = walsender_psql('r_mdb', 'CREATE_REPLICATION_SLOT tmpphys PHYSICAL');
isnt($ret, 0, 'mdb_replication member cannot create physical slots (fails)');
like($err, $perm_err,
	'mdb_replication member cannot create physical slots');

# d) mdb_replication member may use logical slots (database walsender
# connections, which logical decoding requires anyway)
($ret, $out, $err) = walsender_psql('r_mdb',
	'CREATE_REPLICATION_SLOT lslot LOGICAL test_decoding', db => 1);
is($ret, 0, 'mdb_replication member can create a logical slot');
unlike($err, $perm_err, 'no permission error creating a logical slot');

($ret, $out, $err) = walsender_psql('r_mdb',
	'START_REPLICATION SLOT "lslot" LOGICAL 0/0', db => 1);
like($err, $stream_started,
	'mdb_replication member streams from a logical slot (copy-both)');
unlike($err, $perm_err, 'no permission error for logical slot streaming');

done_testing();
