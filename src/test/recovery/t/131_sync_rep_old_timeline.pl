# Copyright (c) 2026, PostgreSQL Global Development Group

# Feedback belongs to one replication stream. A physical stream of an old
# timeline must not confirm commits on the new timeline, including when another
# sender calculates the synchronous positions. Reusing the connection for a new
# stream must not reuse the previous stream's feedback either.
use strict;
use warnings FATAL => 'all';
use IO::Select;
use IO::Socket::IP;
use Socket qw(SOCK_STREAM);
use PostgreSQL::Test::Cluster;
use PostgreSQL::Test::Utils;
use Test::More;

# Use a small replication-protocol client so the test can keep the old stream
# open after the server sends CopyDone, and control when it acknowledges data.
sub read_exact
{
	my ($socket, $length) = @_;
	my $result = '';
	while (length($result) < $length)
	{
		IO::Select->new($socket)->can_read($PostgreSQL::Test::Utils::timeout_default)
		  or die 'timed out reading replication protocol';
		my $n = sysread($socket, my $part, $length - length($result));
		die 'replication connection closed' unless defined($n) && $n > 0;
		$result .= $part;
	}
	return $result;
}

sub read_message
{
	my ($socket) = @_;
	my $type = read_exact($socket, 1);
	my $length = unpack('N', read_exact($socket, 4));
	die 'invalid message length' if $length < 4;
	my $data = read_exact($socket, $length - 4);
	die "replication server error: $data" if $type eq 'E';
	return ($type, $data);
}

sub send_message
{
	my ($socket, $type, $data) = @_;
	print {$socket} $type, pack('N', length($data) + 4), $data
	  or die 'could not write replication message';
}

sub connect_replication
{
	my ($node, $name) = @_;
	my $user = $node->safe_psql('postgres', 'SELECT current_user');
	my $socket = IO::Socket::IP->new(
		PeerHost => '127.0.0.1', PeerPort => $node->port,
		Type => SOCK_STREAM,
		Timeout => $PostgreSQL::Test::Utils::timeout_default)
	  or die "could not connect to replication server: $!";
	$socket->autoflush(1);
	my $startup = pack('N', 196608)
	  . "user\0$user\0replication\0true\0application_name\0$name\0\0";
	print {$socket} pack('N', length($startup) + 4), $startup
	  or die 'could not send startup message';
	while (1)
	{
		my ($type, $data) = read_message($socket);
		die 'test requires trust authentication'
		  if $type eq 'R' && unpack('N', $data) != 0;
		last if $type eq 'Z';
	}
	return $socket;
}

sub start_stream
{
	my ($socket, $lsn, $tli) = @_;
	send_message($socket, 'Q', "START_REPLICATION $lsn TIMELINE $tli\0");
	while (1)
	{
		my ($type) = read_message($socket);
		last if $type eq 'W';
	}
	return;
}

sub lsn_value
{
	my ($lsn) = @_;
	my ($hi, $lo) = split('/', $lsn);
	return hex($hi) * 4294967296 + hex($lo);
}

# Read real WAL bytes, rather than treating the advertised WAL end as received.
# With no target, consume the historical stream up to the server's CopyDone.
sub receive_wal
{
	my ($socket, $target) = @_;
	my $received = 0;
	my $deadline = time() + $PostgreSQL::Test::Utils::timeout_default;
	while (time() <= $deadline)
	{
		my ($type, $data) = read_message($socket);
		if ($type eq 'd' && substr($data, 0, 1) eq 'w')
		{
			$received = unpack('Q>', substr($data, 1, 8)) + length($data) - 25;
			return $received if defined($target) && $received >= $target;
		}
		return $received if $type eq 'c';
	}
	die 'timed out receiving WAL';
}

sub feedback
{
	my ($socket, $lsn, $time) = @_;
	send_message($socket, 'd', pack('aQ>Q>Q>q>C', 'r', $lsn, $lsn, $lsn, $time, 0));
	return;
}

# Observe the second feedback update. Processing it proves the first feedback's
# SyncRepReleaseWaiters call has finished, avoiding a timing-only assertion.
sub feedback_barrier
{
	my ($node, $socket, $name, $lsn, $second) = @_;
	feedback($socket, $lsn, ($second - 1) * 1000000);
	feedback($socket, $lsn, $second * 1000000);
	$node->poll_query_until('postgres',
		"SELECT reply_time = '2000-01-01 00:00:00+00'::timestamptz + interval '$second seconds' FROM pg_stat_replication WHERE application_name = '$name'")
	  or die 'sender did not process feedback';
	return;
}

my $primary = PostgreSQL::Test::Cluster->new('primary');
$primary->init(allows_streaming => 1, extra => ['--wal-segsize' => 1]);
$primary->append_conf('postgresql.conf', q{
listen_addresses = '127.0.0.1'
wal_keep_size = '64MB'
wal_sender_timeout = 0
});
$primary->start;
$primary->safe_psql('postgres', 'CREATE TABLE timeline_data(i int, payload text)');
$primary->backup('backup');
my $start = $primary->safe_psql('postgres', 'SELECT redo_lsn FROM pg_control_checkpoint()');
my $promoted = PostgreSQL::Test::Cluster->new('promoted');
$promoted->init_from_backup($primary, 'backup', has_streaming => 1);
$promoted->start;
$primary->wait_for_catchup($promoted);
$promoted->promote;

# Leave the original primary running on timeline 1 and receive bytes from its
# divergent branch. These are real old-timeline positions beyond the fork.
$primary->safe_psql('postgres',
	'INSERT INTO timeline_data SELECT i, md5(i::text) FROM generate_series(1,50000) i');
my $old_lsn = $primary->safe_psql('postgres', 'SELECT pg_current_wal_flush_lsn()');
my $old_source = connect_replication($primary, 'old_source');
start_stream($old_source, $start, 1);
my $old_received = receive_wal($old_source, lsn_value($old_lsn));
close($old_source);

my $history = slurp_file($promoted->data_dir . '/pg_wal/00000002.history');
my ($fork) = $history =~ /^1\s+(\S+)/m;
ok(defined($fork), 'promotion created timeline 2 history');
my $new_lsn = $promoted->safe_psql('postgres', 'SELECT pg_current_wal_flush_lsn()');
cmp_ok($old_received, '>', lsn_value($new_lsn),
	'client has received old-branch WAL beyond the new primary WAL end');

$promoted->safe_psql('postgres',
	q{ALTER SYSTEM SET synchronous_standby_names = 'ANY 1 (historical, current)'});
$promoted->reload;
$promoted->poll_query_until('postgres',
	q{SELECT current_setting('synchronous_standby_names') = 'ANY 1 (historical, current)'})
	  or die 'synchronous_standby_names not reloaded';
my $old = connect_replication($promoted, 'historical');
start_stream($old, $start, 1);
receive_wal($old, undef);

feedback_barrier($promoted, $old, 'historical', lsn_value($fork), 1);
$promoted->poll_query_until('postgres',
	q{SELECT state = 'streaming' FROM pg_stat_replication WHERE application_name = 'historical'})
	  or die 'historical sender is not streaming';

my $session = $promoted->background_psql('postgres');
$session->set_query_timer_restart;
my $pid = $session->query('SELECT pg_backend_pid()');
$session->query_until(qr//,
	"INSERT INTO timeline_data VALUES (1, 'new timeline'); SELECT 'commit one';\n");
$promoted->poll_query_until('postgres',
	"SELECT wait_event = 'SyncRep' FROM pg_stat_activity WHERE pid = $pid")
	  or die 'new-timeline commit did not wait for replication';
my $commit = $promoted->safe_psql('postgres', 'SELECT pg_current_wal_flush_lsn()');
cmp_ok($old_received, '>', lsn_value($commit),
	'old-branch feedback is numerically ahead of the new commit');
feedback_barrier($promoted, $old, 'historical', $old_received, 2);
is($promoted->safe_psql('postgres',
	"SELECT wait_event FROM pg_stat_activity WHERE pid = $pid"),
	'SyncRep', 'old-timeline feedback cannot release a new-timeline commit');
is($promoted->safe_psql('postgres',
	q{SELECT sync_state FROM pg_stat_replication WHERE application_name = 'historical'}),
	'potential', 'historical physical stream is not an active synchronous standby');

my $current = connect_replication($promoted, 'current');
start_stream($current, $fork, 2);
my $current_received = receive_wal($current, lsn_value($commit));
feedback_barrier($promoted, $current, 'current', lsn_value($fork), 4);
is($promoted->safe_psql('postgres',
	"SELECT wait_event FROM pg_stat_activity WHERE pid = $pid"),
	'SyncRep', 'another sender also excludes the old-timeline candidate');
feedback_barrier($promoted, $current, 'current', $current_received, 6);
ok(pump_until($session->{run}, $session->{timeout}, \$session->{stdout}, qr/commit one/),
	'current-timeline feedback releases the commit');
$session->{stdout} = '';
$session->quit;
close($current);

# Finish the old COPY and use the same server process for the current timeline.
# Its old high feedback must not be reused before this new stream replies.
my $sender_pid = $promoted->safe_psql('postgres',
	q{SELECT pid FROM pg_stat_replication WHERE application_name = 'historical'});
send_message($old, 'c', '');
while (1)
{
	my ($type) = read_message($old);
	last if $type eq 'Z';
}
start_stream($old, $fork, 2);
my $restart_received = receive_wal($old, lsn_value($commit));
is($promoted->safe_psql('postgres',
	q{SELECT pid FROM pg_stat_replication WHERE application_name = 'historical'}),
	$sender_pid, 'new stream reuses the same WAL sender');
is($promoted->safe_psql('postgres',
	q{SELECT write_lsn IS NULL AND flush_lsn IS NULL AND replay_lsn IS NULL FROM pg_stat_replication WHERE application_name = 'historical'}),
	't', 'new stream clears all feedback from the previous timeline');
feedback_barrier($promoted, $old, 'historical', $restart_received, 8);
is($promoted->safe_psql('postgres',
	q{SELECT sync_state FROM pg_stat_replication WHERE application_name = 'historical'}),
	'quorum', 'restarted current-timeline stream can become synchronous');
close($old);
$promoted->stop;
$primary->stop;
done_testing();
