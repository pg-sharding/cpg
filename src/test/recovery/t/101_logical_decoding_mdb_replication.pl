# Testing of logical decoding using SQL interface and/or pg_recvlogical
#
# Most logical decoding tests are in contrib/test_decoding. This module
# is for work that doesn't fit well there, like where server restarts
# are required.
use strict;
use warnings;
use PostgreSQL::Test::Cluster;
use PostgreSQL::Test::Utils;
use Test::More tests => 10;
use Config;


# Initialize master node
my $node_master = PostgreSQL::Test::Cluster->new('master');
$node_master->init(allows_streaming => 1);
$node_master->append_conf(
	'postgresql.conf', qq(
wal_level = logical
));
$node_master->start;
my $backup_name = 'master_backup';

$node_master->safe_psql('postgres',
	"SET password_encryption='md5'; CREATE ROLE normal LOGIN PASSWORD 'pass';");
$node_master->safe_psql('postgres',
	"GRANT CREATE ON DATABASE postgres TO normal;");
$node_master->safe_psql('postgres',
	"GRANT ALL ON SCHEMA public TO normal;");
$node_master->safe_psql('postgres',
	"CREATE ROLE mdb_replication NOLOGIN;");
$node_master->safe_psql('postgres',
	"GRANT mdb_replication TO normal;");

$node_master->safe_psql('postgres',
	qq[CREATE TABLE decoding_test(x integer, y text);], extra_params => [ '-U', 'normal' ]);

$node_master->safe_psql('postgres',
	qq[SELECT pg_create_logical_replication_slot('test_slot', 'test_decoding');],
	extra_params => [ '-U', 'normal' ]);

$node_master->safe_psql('postgres',
	qq[INSERT INTO decoding_test(x,y) SELECT s, s::text FROM generate_series(1,10) s;],
	extra_params => [ '-U', 'normal' ]
);

# Basic decoding works
my ($result) = $node_master->safe_psql('postgres',
	qq[SELECT pg_logical_slot_get_changes('test_slot', NULL, NULL);],
	extra_params => [ '-U', 'normal' ]);
is(scalar(my @foobar = split /^/m, $result),
	12, 'Decoding produced 12 rows inc BEGIN/COMMIT');

# If we immediately crash the server we might lose the progress we just made
# and replay the same changes again. But a clean shutdown should never repeat
# the same changes when we use the SQL decoding interface.
$node_master->restart('fast');

# There are no new writes, so the result should be empty.
$result = $node_master->safe_psql('postgres',
	qq[SELECT pg_logical_slot_get_changes('test_slot', NULL, NULL);],
	extra_params => [ '-U', 'normal' ]);
chomp($result);
is($result, '', 'Decoding after fast restart repeats no rows');

# Insert some rows and verify that we get the same results from pg_recvlogical
# and the SQL interface.
$node_master->safe_psql('postgres',
	qq[INSERT INTO decoding_test(x,y) SELECT s, s::text FROM generate_series(1,4) s;],
	extra_params => [ '-U', 'normal' ]
);

my $expected = q{BEGIN
table public.decoding_test: INSERT: x[integer]:1 y[text]:'1'
table public.decoding_test: INSERT: x[integer]:2 y[text]:'2'
table public.decoding_test: INSERT: x[integer]:3 y[text]:'3'
table public.decoding_test: INSERT: x[integer]:4 y[text]:'4'
COMMIT};

my $stdout_sql = $node_master->safe_psql('postgres',
	qq[SELECT data FROM pg_logical_slot_peek_changes('test_slot', NULL, NULL, 'include-xids', '0', 'skip-empty-xacts', '1');],
	extra_params => [ '-U', 'normal' ]
);
is($stdout_sql, $expected, 'got expected output from SQL decoding session');

my $endpos = $node_master->safe_psql('postgres',
	"SELECT lsn FROM pg_logical_slot_peek_changes('test_slot', NULL, NULL) ORDER BY lsn DESC LIMIT 1;",
	extra_params => [ '-U', 'normal' ]
);
print "waiting to replay $endpos\n";

my $stdout_recv = $node_master->pg_recvlogical_upto(
	'postgres', 'test_slot', $endpos, 180,
	'include-xids'     => '0',
	'skip-empty-xacts' => '1');
chomp($stdout_recv);
is($stdout_recv, $expected,
	'got same expected output from pg_recvlogical decoding session');

$node_master->poll_query_until('postgres',
	"SELECT EXISTS (SELECT 1 FROM pg_replication_slots WHERE slot_name = 'test_slot' AND active_pid IS NULL)"
) or die "slot never became inactive";

$stdout_recv = $node_master->pg_recvlogical_upto(
	'postgres', 'test_slot', $endpos, 180,
	'include-xids'     => '0',
	'skip-empty-xacts' => '1');
chomp($stdout_recv);
is($stdout_recv, '',
	'pg_recvlogical acknowledged changes, nothing pending on slot');

$node_master->safe_psql('postgres', 'CREATE DATABASE otherdb');

is( $node_master->psql(
		'otherdb',
		"SELECT lsn FROM pg_logical_slot_peek_changes('test_slot', NULL, NULL) ORDER BY lsn DESC LIMIT 1;",
		extra_params => [ '-U', 'normal' ]
	),
	3,
	'replaying logical slot from another database fails');

$node_master->safe_psql('otherdb',
	qq[SELECT pg_create_logical_replication_slot('otherdb_slot', 'test_decoding');],
	extra_params => [ '-U', 'normal' ]
);

# make sure you can't drop a slot while active
SKIP:
{

	# some Windows Perls at least don't like IPC::Run's start/kill_kill regime.
	skip "Test fails on Windows perl", 2 if $Config{osname} eq 'MSWin32';

	my $pg_recvlogical = IPC::Run::start(
		[
			'pg_recvlogical', '-d', $node_master->connstr('otherdb'),
			'-S', 'otherdb_slot', '-f', '-', '--start', '-U' , 'normal'
		]);
	$node_master->poll_query_until('otherdb',
		"SELECT EXISTS (SELECT 1 FROM pg_replication_slots WHERE slot_name = 'otherdb_slot' AND active_pid IS NOT NULL)"
	) or die "slot never became active";
	is($node_master->psql('postgres', 'DROP DATABASE otherdb'),
		3, 'dropping a DB with active logical slots fails');
	$pg_recvlogical->kill_kill;
	is($node_master->slot('otherdb_slot')->{'slot_name'},
		undef, 'logical slot still exists');
}

$node_master->poll_query_until('otherdb',
	"SELECT EXISTS (SELECT 1 FROM pg_replication_slots WHERE slot_name = 'otherdb_slot' AND active_pid IS NULL)",
) or die "slot never became inactive";

is($node_master->psql('postgres', 'DROP DATABASE otherdb'),
	0, 'dropping a DB with inactive logical slots succeeds');
is($node_master->slot('otherdb_slot')->{'slot_name'},
	undef, 'logical slot was actually dropped with DB');

# done with the node
$node_master->stop;
