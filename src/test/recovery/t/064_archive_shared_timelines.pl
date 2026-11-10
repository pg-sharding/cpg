# Copyright (c) 2026, PostgreSQL Global Development Group

# Stream a timeline change through a cascading standby while archiving is
# unavailable.  Fetched history must remain pending until it can be archived.
use strict;
use warnings FATAL => 'all';
use PostgreSQL::Test::Cluster;
use PostgreSQL::Test::Utils;
use Test::More;

my $archive = PostgreSQL::Test::Utils::tempdir();
my $copy = $PostgreSQL::Test::Utils::windows_os
  ? qq{copy "%p" "$archive\\%f"}
  : qq{cp "%p" "$archive/%f"};

my $broken=$PostgreSQL::Test::Utils::windows_os
 ? q{copy "%p_does_not_exist" "%f_does_not_exist"}
 : q{cp "%p_does_not_exist" "%f_does_not_exist"};

for my $mode ('always','shared')
{
 my $a=PostgreSQL::Test::Cluster->new("old_$mode");
 $a->init(allows_streaming=>1,extra=>['--wal-segsize'=>1]);
 $a->append_conf('postgresql.conf',"archive_mode=on\narchive_command='$broken'\nwal_keep_size='64MB'\n");
 $a->start;
 $a->backup('to_middle');
 my $b=PostgreSQL::Test::Cluster->new("middle_$mode");
 $b->init_from_backup($a,'to_middle',has_streaming=>1);
 $b->append_conf('postgresql.conf',"archive_mode=$mode\narchive_status_report_interval='100ms'\narchive_command='$broken'\n");
 $b->start;
 $a->wait_for_catchup($b);
 $b->backup('to_leaf');
 my $c=PostgreSQL::Test::Cluster->new("leaf_$mode");
 $c->init_from_backup($b,'to_leaf',has_streaming=>1);
 $c->append_conf('postgresql.conf',"archive_mode=$mode\narchive_status_report_interval='100ms'\narchive_command='$broken'\n");
 $c->start;
 $b->wait_for_catchup($c);

 # Move to a new segment after both backups, so status files in the backup
 # cannot satisfy the before/after checks for the tested segment.
 $a->safe_psql('postgres',q{SELECT txid_current(); SELECT pg_switch_wal(); CREATE TABLE handover_guard(i int); INSERT INTO handover_guard VALUES(42);});
 $a->wait_for_catchup($b);
 $b->wait_for_catchup($c);
 my $wal=$a->safe_psql('postgres',q{SELECT pg_walfile_name(pg_current_wal_lsn())});
 my $status=$c->data_dir.'/pg_wal/archive_status';
 ok(-f $c->data_dir."/pg_wal/$wal","$mode: active old-timeline WAL exists before promotion");
 ok(!-f "$status/$wal.done","$mode: active segment is not already marked done");
 is($a->safe_psql('postgres',q{SELECT archived_count FROM pg_stat_archiver}),0,"$mode: old primary has archived nothing");

 $a->stop('immediate');
 $b->promote;
 $b->safe_psql('postgres',q{INSERT INTO handover_guard VALUES(43); CHECKPOINT;});
 $b->wait_for_catchup($c);
 $c->poll_query_until('postgres',q{SELECT received_tli=2 FROM pg_stat_wal_receiver})
  or die 'leaf did not switch to timeline 2';
 is($c->safe_psql('postgres',q{SELECT sum(i) FROM handover_guard}),85,"$mode: data reaches the leaf on new timeline");
 is($b->safe_psql('postgres',q{SELECT archived_count FROM pg_stat_archiver}),0,"$mode: promoted middle has archived nothing");
 is($c->safe_psql('postgres',q{SELECT archived_count FROM pg_stat_archiver}),0,"$mode: leaf has archived nothing");
 is($c->safe_psql('postgres',q{SELECT coalesce(primary_last_archived,'') FROM pg_stat_wal_receiver}), '',"$mode: leaf received no archive report");
 my $history='00000002.history';
 ok(-f $c->data_dir."/pg_wal/$history","$mode: descendant timeline history was fetched");
 ok(!-f "$status/$history.done","$mode: unconfirmed history file must not be marked archived");
 ok(-f "$status/$history.ready","$mode: fetched history file remains pending archival");
 # On promotion, this node must actually archive the fetched history.
 # Use a per-mode directory so an earlier iteration cannot satisfy the check.
 my $destination = "$archive/$mode";
 mkdir($destination) or die "mkdir $destination: $!";
 my $archive_command = $copy;
 $archive_command =~ s/\Q$archive\E/$destination/g;
 $b->stop('immediate');
 $c->promote;
 $c->safe_psql('postgres', "ALTER SYSTEM SET archive_command = '$archive_command'");
 $c->reload;
 $c->poll_query_until('postgres',
   "SELECT (pg_stat_file('pg_wal/archive_status/$history.done', true)).size IS NOT NULL")
   or die 'promoted leaf did not archive the fetched history';
 ok(-f "$destination/$history", "$mode: fetched history is archived after promotion");
 is(slurp_file("$destination/$history"),
    slurp_file($c->data_dir . "/pg_wal/$history"),
    "$mode: archived history matches the streamed file");
 $c->stop;
}
done_testing();
