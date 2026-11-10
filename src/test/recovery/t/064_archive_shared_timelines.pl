# Copyright (c) 2026, PostgreSQL Global Development Group

# Stream a timeline change through a cascading standby while archiving is
# unavailable.  Received WAL and history must remain pending until archived.
use strict;
use warnings FATAL => 'all';
use PostgreSQL::Test::Cluster;
use PostgreSQL::Test::Utils;
use Test::More;
use Digest::SHA qw(sha256_hex);

for my $mode ('always', 'shared')
{
	my $archive = PostgreSQL::Test::Utils::tempdir();
	my $copy = $PostgreSQL::Test::Utils::windows_os
	  ? qq{copy "%p" "$archive\\%f"}
	  : qq{cp "%p" "$archive/%f"};

	my $a = PostgreSQL::Test::Cluster->new("old_$mode");
	$a->init(allows_streaming => 1, extra => ['--wal-segsize' => 1]);
	$a->append_conf(
		'postgresql.conf', qq(
archive_mode = on
archive_command = ''
wal_keep_size = '64MB'
));
	$a->start;
	$a->backup('to_middle');

	my $b = PostgreSQL::Test::Cluster->new("middle_$mode");
	$b->init_from_backup($a, 'to_middle', has_streaming => 1);
	$b->append_conf(
		'postgresql.conf', qq(
archive_mode = $mode
archive_status_report_interval = '100ms'
));
	$b->start;
	$a->wait_for_catchup($b);
	$b->backup('to_leaf');

	my $c = PostgreSQL::Test::Cluster->new("leaf_$mode");
	$c->init_from_backup($b, 'to_leaf', has_streaming => 1);
	$c->append_conf(
		'postgresql.conf', qq(
archive_mode = $mode
archive_status_report_interval = '100ms'
));
	$c->start;
	$b->wait_for_catchup($c);

	# Move past both backups, so copied status files cannot satisfy the checks.
	$a->safe_psql(
		'postgres', q{
SELECT txid_current();
SELECT pg_switch_wal();
CREATE TABLE handover_guard(i int);
INSERT INTO handover_guard VALUES (42);
});
	$a->wait_for_catchup($b);
	$b->wait_for_catchup($c);
	my $wal = $a->safe_psql('postgres',
		'SELECT pg_walfile_name(pg_current_wal_lsn())');
	my $status = $c->data_dir . '/pg_wal/archive_status';
	ok(-f $c->data_dir . "/pg_wal/$wal",
		"$mode: active old-timeline WAL exists before promotion");
	ok(!-f "$status/$wal.done",
		"$mode: active segment is not already marked done");
	is($a->safe_psql('postgres',
			'SELECT archived_count FROM pg_stat_archiver'),
		0, "$mode: old primary has archived nothing");

	# Immediate shutdown leaves the active segment incomplete.  A clean
	# shutdown would finish it and miss the end-of-historical-stream case.
	$a->stop('immediate');
	$b->promote;
	$b->safe_psql('postgres',
		'INSERT INTO handover_guard VALUES (43); CHECKPOINT');
	$b->wait_for_catchup($c);
	$c->poll_query_until('postgres',
		'SELECT received_tli = 2 FROM pg_stat_wal_receiver')
	  or die 'leaf did not switch to timeline 2';
	is($c->safe_psql('postgres', 'SELECT sum(i) FROM handover_guard'),
		85, "$mode: data reaches the leaf on the new timeline");
	for my $node ($b, $c)
	{
		is($node->safe_psql('postgres',
				'SELECT archived_count FROM pg_stat_archiver'),
			0, "$mode: " . $node->name . ' has archived nothing');
	}
	is($c->safe_psql('postgres',
			q{SELECT coalesce(primary_last_archived, '') FROM pg_stat_wal_receiver}),
		'', "$mode: leaf received no archive report");

	my $history = '00000002.history';
	ok(-f $c->data_dir . "/pg_wal/$history",
		"$mode: descendant timeline history was fetched");
	ok(!-f "$status/$history.done",
		"$mode: unconfirmed history is not marked archived");
	ok(-f "$status/$history.ready",
		"$mode: fetched history remains pending");
	ok(!-f "$status/$wal.done",
		"$mode: unconfirmed historical WAL is not marked archived");
	ok(-f "$status/$wal.ready", "$mode: historical WAL remains pending");
	my $wal_hash = sha256_hex(slurp_file($c->data_dir . "/pg_wal/$wal"));
	my $partial = $b->safe_psql('postgres',
		'SELECT pg_walfile_name(pg_current_wal_lsn())') . '.partial';

	# Promotion must archive the pending files.  Each iteration has its own
	# destination, so the always-mode control cannot satisfy shared checks.
	$b->stop('immediate');
	$c->promote;
	$c->safe_psql('postgres', "ALTER SYSTEM SET archive_command = '$copy'");
	$c->reload;
	for my $file ($history, $wal, $partial)
	{
		$c->poll_query_until('postgres',
			"SELECT (pg_stat_file('pg_wal/archive_status/$file.done', true)).size IS NOT NULL")
		  or die "promoted leaf did not archive $file";
		ok(-f "$archive/$file", "$mode: promoted leaf archived $file");
	}
	is(slurp_file("$archive/$history"),
		slurp_file($c->data_dir . "/pg_wal/$history"),
		"$mode: archived history matches the streamed file");
	is(sha256_hex(slurp_file("$archive/$wal")), $wal_hash,
		"$mode: archived historical WAL matches the streamed segment");
	$c->stop;
}
done_testing();
