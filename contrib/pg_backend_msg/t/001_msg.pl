# Copyright (c) 2026, PostgreSQL Global Development Group

# Test messages passed via pg_cancel_backend() / pg_terminate_backend(),
# provided by the pg_backend_msg extension.

use strict;
use warnings;

use IPC::Run qw(start finish timer);
use PostgreSQL::Test::Cluster;
use PostgreSQL::Test::Utils;
use Test::More;

my $node = PostgreSQL::Test::Cluster->new('main');
$node->init;
$node->start;

$node->safe_psql('postgres', 'CREATE EXTENSION pg_backend_msg');

# Start a session running a long query, identified by application_name.
sub start_victim
{
	my $out = '';
	my $err = '';
	my $victim = start(
		[
			'psql', '-X', '-A', '-t', '-v', 'ON_ERROR_STOP=0',
			'-d', $node->connstr('postgres'),
			'-c', "SET application_name = 'pg_backend_msg_victim'; SELECT pg_sleep(60);"
		],
		'>', \$out,
		'2>', \$err,
		timer(60));
	my $pid = $node->safe_psql('postgres',
		"SELECT pid FROM pg_stat_activity WHERE application_name = 'pg_backend_msg_victim'");
	isnt($pid, '', 'victim backend found');
	return ($victim, \$out, \$err, $pid);
}

# pg_cancel_backend() with a message
{
	my ($victim, $out, $err, $pid) = start_victim();

	my $result = $node->safe_psql('postgres',
		"SELECT pg_cancel_backend($pid, 'test cancel message')");
	is($result, 't', 'pg_cancel_backend with message succeeded');

	finish $victim;
	like(${$err}, qr/canceling statement due to user request: test cancel message/,
		'victim saw the cancel message');
}

# pg_terminate_backend() with a message
{
	my ($victim, $out, $err, $pid) = start_victim();

	my $result = $node->safe_psql('postgres',
		"SELECT pg_terminate_backend($pid, 0, 'test terminate message')");
	is($result, 't', 'pg_terminate_backend with message succeeded');

	finish $victim;
	like(${$err}, qr/terminating connection due to administrator command: test terminate message/,
		'victim saw the terminate message');
}

# pg_terminate_backend() with named arguments
{
	my ($victim, $out, $err, $pid) = start_victim();

	my $result = $node->safe_psql('postgres',
		"SELECT pg_terminate_backend(pid => $pid, timeout => 0, message => 'named args work')");
	is($result, 't', 'pg_terminate_backend with named arguments succeeded');

	finish $victim;
	like(${$err}, qr/terminating connection due to administrator command: named args work/,
		'victim saw the terminate message');
}

# A too long message is truncated, with a NOTICE for the caller
{
	my ($victim, $out, $err, $pid) = start_victim();

	my ($ret, $stdout, $stderr) = $node->psql('postgres',
		"SELECT pg_cancel_backend($pid, repeat('xyz', 100))");
	is($ret, 0, 'pg_cancel_backend with long message succeeded');
	is($stdout, 't', 'pg_cancel_backend with long message returned true');
	like($stderr, qr/message is too long and was truncated to 127 bytes/,
		'caller was told about the truncation');

	finish $victim;
	like(${$err}, qr/canceling statement due to user request: (?:xyz){42}x/,
		'victim saw the truncated cancel message');
}

# The old signatures keep working with the extension in place
{
	my ($ret, $stdout, $stderr) = $node->psql('postgres',
		'SELECT pg_cancel_backend(999999999)');
	is($ret, 0, 'pg_cancel_backend() with one argument succeeded');
	is($stdout, 'f', 'pg_cancel_backend() with one argument returned false');
	like($stderr, qr/PID 999999999 is not a PostgreSQL backend process/,
		'pg_cancel_backend() warns about missing backend');

	($ret, $stdout, $stderr) = $node->psql('postgres',
		'SELECT pg_terminate_backend(999999999, 0)');
	is($ret, 0, 'pg_terminate_backend() with two arguments succeeded');
	is($stdout, 'f', 'pg_terminate_backend() with two arguments returned false');
	like($stderr, qr/PID 999999999 is not a PostgreSQL backend process/,
		'pg_terminate_backend() warns about missing backend');
}

$node->stop('fast');

done_testing();
