# Copyright (c) 2026, PostgreSQL Global Development Group

# A cascading sender can fetch WAL that it no longer retains.  Exercise both
# an upstream that retains the segment and one that must restore it from its
# archive.  The intermediate standby and the leaf have no archive access.
use strict;
use warnings FATAL => 'all';

use FindBin;
use PostgreSQL::Test::Cluster;
use PostgreSQL::Test::Utils;
use Test::More;

my $helper = "$FindBin::RealBin/walsender_restore";
my $rows = q{SELECT string_agg(i::text, ',' ORDER BY i) FROM fetch_test};
my $scratch_count = q{SELECT count(*) FROM pg_ls_dir('pg_wal') AS f
  WHERE f LIKE 'xlogtemp.%.walsender'};

for my $from_archive (0, 1)
{
	subtest $from_archive ? 'upstream archive' : 'upstream pg_wal' => sub {
		my $label = $from_archive ? 'archive' : 'retained';
		my $primary = PostgreSQL::Test::Cluster->new("primary_$label");
		$primary->init(
			allows_streaming => 1,
			has_archiving => $from_archive,
			extra => ['--wal-segsize=1']);
		my $keep = $from_archive ? 0 : 128;
		$primary->append_conf(
			'postgresql.conf', qq(
min_wal_size = '2MB'
max_wal_size = '4MB'
wal_keep_size = '${keep}MB'
checkpoint_timeout = '1h'
log_min_messages = debug1
));
		$primary->start;
		$primary->safe_psql('postgres', 'CREATE TABLE fetch_test (i int)');
		$primary->backup('base');
		$primary->safe_psql('postgres',
			q{SELECT pg_create_physical_replication_slot('middle_slot')});

		my $middle = PostgreSQL::Test::Cluster->new("middle_$label");
		$middle->init_from_backup($primary, 'base', has_streaming => 1);
		$middle->append_conf(
			'postgresql.conf', qq(
primary_slot_name = 'middle_slot'
wal_keep_size = 0
restore_command = ''
log_min_messages = debug1
));
		$middle->start;

		my $leaf = PostgreSQL::Test::Cluster->new("leaf_$label");
		$leaf->init_from_backup($primary, 'base', has_streaming => 1);
		$leaf->enable_streaming($middle);
		$leaf->append_conf(
			'postgresql.conf', qq(
restore_command = ''
wal_retrieve_retry_interval = '100ms'
));
		$leaf->start;
		$primary->safe_psql('postgres', 'INSERT INTO fetch_test VALUES (1)');
		my $initial_lsn = $primary->lsn('insert');
		$primary->wait_for_catchup($middle, 'replay', $initial_lsn);
		$middle->wait_for_catchup($leaf, 'replay', $initial_lsn);
		$leaf->stop;
		my $old_segment = $primary->safe_psql('postgres',
			"SELECT pg_walfile_name('$initial_lsn')");
		my $walreceiver_pid = $middle->safe_psql('postgres',
			'SELECT pid FROM pg_stat_wal_receiver');

		$primary->safe_psql('postgres', 'INSERT INTO fetch_test VALUES (2)');
		$primary->advance_wal(10);
		$primary->safe_psql('postgres', 'CHECKPOINT');
		my $target_lsn = $primary->lsn('insert');
		$primary->wait_for_catchup($middle, 'replay', $target_lsn);
		if ($from_archive)
		{
			$primary->poll_query_until('postgres',
				"SELECT last_archived_wal > '$old_segment' FROM pg_stat_archiver")
			  or BAIL_OUT('archive did not advance');
			$primary->safe_psql('postgres', 'CHECKPOINT');
			$primary->wait_for_catchup($middle, 'replay',
				$primary->lsn('insert'));
		}
		$middle->safe_psql('postgres', 'CHECKPOINT');
		ok(!-e $middle->data_dir . "/pg_wal/$old_segment",
			'required WAL was removed from intermediate standby')
		  or BAIL_OUT('restartpoint did not remove old WAL');

		if ($from_archive)
		{
			ok(!-e $primary->data_dir . "/pg_wal/$old_segment",
				'required WAL was also removed from primary');
			ok(-f $primary->archive_dir . "/$old_segment",
				'primary archive contains required WAL');
		}
		else
		{
			ok(-f $primary->data_dir . "/pg_wal/$old_segment",
				'primary still retains required WAL');
		}

		# The default behavior is unchanged: a cascading sender cannot bridge
		# the gap, even though primary_conninfo is configured.
		my $offset = -s $middle->logfile;
		$leaf->start;
		$middle->wait_for_log(
			qr/requested WAL segment .* has already been removed/, $offset);
		$leaf->stop;
		$middle->poll_query_until('postgres',
			'SELECT count(*) = 0 FROM pg_stat_replication')
		  or BAIL_OUT('disabled-fallback sender did not exit');
		is($middle->safe_psql('postgres', $scratch_count),
			'0', 'disabled fetch leaves no private files');

		$middle->append_conf('postgresql.conf', 'wal_sender_fetch = on');
		$middle->reload;
		$middle->poll_query_until('postgres',
			q{SELECT current_setting('wal_sender_fetch')::boolean})
		  or BAIL_OUT('fetch was not enabled');

		if ($from_archive)
		{
			# Initially the primary cannot supply the missing segment either.
			# A failed upstream stream must release the connection.
			$offset = -s $middle->logfile;
			$leaf->start;
			$middle->wait_for_log(
				qr/(?:could not start WAL streaming|could not receive data from WAL stream):[^\n]*has already been removed/,
				$offset);
			$leaf->stop;
			$middle->poll_query_until('postgres',
				'SELECT count(*) = 0 FROM pg_stat_replication')
			  or BAIL_OUT('failed-fetch sender did not exit');
			$primary->poll_query_until('postgres',
				'SELECT count(*) = 1 FROM pg_stat_replication')
			  or BAIL_OUT('failed fetch left an upstream connection');
			is($middle->safe_psql('postgres', $scratch_count),
				'0', 'failed fetch leaves no private files');

			my $archive = $primary->archive_dir;
			my $restore = qq{"$^X" "$helper" "$archive" "%f" "%p" "%r"};
			$restore =~ s/\\/\\\\/g;
			$restore =~ s/'/''/g;
			$primary->append_conf(
				'postgresql.conf', qq(
restore_command = '$restore'
wal_sender_restore = on
));
			$primary->reload;
			$primary->poll_query_until('postgres',
				q{SELECT current_setting('wal_sender_restore')::boolean})
			  or BAIL_OUT('upstream archive fallback was not enabled');
		}

		my $primary_offset = -s $primary->logfile;
		$offset = -s $middle->logfile;
		$leaf->start;
		$middle->wait_for_catchup($leaf, 'replay', $target_lsn);
		is($leaf->safe_psql('postgres', $rows),
			'1,2', 'leaf replayed WAL fetched through intermediate standby');
		like(slurp_file($middle->logfile, $offset),
			qr/fetched WAL segment \Q$old_segment\E from upstream/,
			'cascading sender used the upstream fetch path');
		if ($from_archive)
		{
			like(slurp_file($primary->logfile, $primary_offset),
				qr/restored log file "\Q$old_segment\E" from archive/,
				'upstream sender supplied WAL from its archive');
		}
		ok(!-e $middle->data_dir . "/pg_wal/$old_segment",
			'fetched WAL was not installed as ordinary local WAL');
		is($middle->safe_psql('postgres',
			'SELECT pid FROM pg_stat_wal_receiver'),
			$walreceiver_pid, 'normal walreceiver connection survived fetches');
		is($primary->safe_psql('postgres',
			q{SELECT string_agg(slot_name, ',') FROM pg_replication_slots}),
			'middle_slot', 'fetches created no replication slots');
		$middle->poll_query_until('postgres', $scratch_count, '0')
		  or BAIL_OUT('completed fetch left a private file');

		my $sender_pid = $middle->safe_psql('postgres',
			'SELECT pid FROM pg_stat_replication');
		$primary->safe_psql('postgres', 'INSERT INTO fetch_test VALUES (3)');
		my $live_lsn = $primary->lsn('insert');
		$primary->wait_for_catchup($middle, 'replay', $live_lsn);
		$middle->wait_for_catchup($leaf, 'replay', $live_lsn);
		is($leaf->safe_psql('postgres', $rows),
			'1,2,3', 'leaf continues with live WAL');
		is($middle->safe_psql('postgres',
			'SELECT pid FROM pg_stat_replication'),
			$sender_pid, 'same downstream connection continues after catchup');
		$leaf->stop;

		# Both forks fit in the same segment.  Fetching an ancestor timeline
		# must stop at its fork, rather than wait for a full segment that the
		# upstream will never send on that timeline.
		my $fork_segment = $primary->safe_psql('postgres',
			'SELECT pg_walfile_name(pg_current_wal_insert_lsn())');
		my $suffix = substr($fork_segment, 8);
		for my $switch (1 .. 2)
		{
			$primary->stop('immediate');
			$primary->set_standby_mode;
			$primary->start;
			$primary->promote;
			my $value = $switch + 3;
			$primary->safe_psql('postgres',
				"INSERT INTO fetch_test VALUES ($value)");
			is($primary->safe_psql('postgres',
				'SELECT pg_walfile_name(pg_current_wal_insert_lsn())'),
				sprintf('%08X%s', $switch + 1, $suffix),
				"promotion $switch stayed within the same segment")
			  or BAIL_OUT('promotion crossed a segment boundary');
		}
		my $fork_target = $primary->lsn('insert');
		$primary->advance_wal(10);
		$primary->safe_psql('postgres', 'CHECKPOINT');
		if ($from_archive)
		{
			my $descendant = "00000003$suffix";
			$primary->poll_query_until('postgres',
				"SELECT last_archived_wal > '$descendant' FROM pg_stat_archiver")
			  or BAIL_OUT('descendant WAL was not archived');
			$primary->safe_psql('postgres', 'CHECKPOINT');
		}
		$primary->wait_for_catchup($middle, 'replay',
			$primary->lsn('insert'));
		$middle->safe_psql('postgres', 'CHECKPOINT');
		for my $tli (1 .. 3)
		{
			my $segment = sprintf('%08X%s', $tli, $suffix);
			ok(!-e $middle->data_dir . "/pg_wal/$segment",
				"intermediate standby no longer retains $segment")
			  or BAIL_OUT('intermediate standby retained fork WAL');
		}
		$offset = -s $middle->logfile;
		$leaf->start;
		$middle->wait_for_catchup($leaf, 'replay', $fork_target);
		is($leaf->safe_psql('postgres', $rows),
			'1,2,3,4,5', 'fetch crosses two forks within one segment');
		like(slurp_file($middle->logfile, $offset),
			qr/fetched WAL segment 00000003\Q$suffix\E from upstream/,
			'fetch used the segment containing the timeline forks');
		$leaf->stop;
		$middle->stop;
		$primary->stop;
	};
}

done_testing();
