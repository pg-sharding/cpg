
# Copyright (c) 2021-2023, PostgreSQL Global Development Group

# Test that logical replication respects permissions
use strict;
use warnings;
use PostgreSQL::Test::Cluster;
use Test::More;

my ($node_publisher, $node_subscriber, $publisher_connstr, $result, $offset);
$offset = 0;

sub publish_insert
{
	my ($tbl, $new_i) = @_;
	$node_publisher->safe_psql(
		'postgres', qq(
  SET SESSION AUTHORIZATION regress_user1;
  INSERT INTO $tbl (i) VALUES ($new_i);
  ));
}

sub publish_update
{
	my ($tbl, $old_i, $new_i) = @_;
	$node_publisher->safe_psql(
		'postgres', qq(
  SET SESSION AUTHORIZATION regress_user1;
  UPDATE $tbl SET i = $new_i WHERE i = $old_i;
  ));
}

sub publish_delete
{
	my ($tbl, $old_i) = @_;
	$node_publisher->safe_psql(
		'postgres', qq(
  SET SESSION AUTHORIZATION regress_user1;
  DELETE FROM $tbl WHERE i = $old_i;
  ));
}


sub publish_truncate
{
	my ($tbl) = @_;
	$node_publisher->safe_psql(
		'postgres', qq(
  SET SESSION AUTHORIZATION regress_user1;
  TRUNCATE $tbl;
  ));
}

sub expect_replication
{
	my ($tbl, $cnt, $min, $max, $testname) = @_;
	$node_publisher->wait_for_catchup('app_test_mdb_admin_sub');
	$result = $node_subscriber->safe_psql(
		'postgres', qq(
  SELECT COUNT(i), MIN(i), MAX(i) FROM $tbl));
	is($result, "$cnt|$min|$max", $testname);
}

sub expect_failure
{
	my ($tbl, $cnt, $min, $max, $re, $testname) = @_;
	$offset = $node_subscriber->wait_for_log($re, $offset);
	$result = $node_subscriber->safe_psql(
		'postgres', qq(
  SELECT COUNT(i), MIN(i), MAX(i) FROM $tbl));
	is($result, "$cnt|$min|$max", $testname);
}

# Create publisher and subscriber nodes with schemas owned and published by
# "regress_alice" but subscribed and replicated by different role
# "regress_admin".  For partitioned tables, layout the partitions differently
# on the publisher than on the subscriber.
#
$node_publisher = PostgreSQL::Test::Cluster->new('publisher');
$node_subscriber = PostgreSQL::Test::Cluster->new('subscriber');
$node_publisher->init(allows_streaming => 'logical');
$node_subscriber->init;
$node_publisher->start;
$node_subscriber->start;
$publisher_connstr = $node_publisher->connstr . ' dbname=postgres';

for my $node ($node_publisher, $node_subscriber)
{
	$node->safe_psql(
		'postgres', qq(
  CREATE ROLE mdb_admin;
  GRANT pg_create_subscription TO mdb_admin;
  CREATE ROLE mdb_replication;

  CREATE ROLE regress_user1 NOSUPERUSER LOGIN PASSWORD 'regress_lolkekpassword';
  CREATE ROLE regress_user2 NOSUPERUSER LOGIN PASSWORD 'regress_lolkekpassword';

  GRANT CREATE ON DATABASE postgres TO regress_user1;
  GRANT CREATE ON DATABASE postgres TO regress_user2;
  SET SESSION AUTHORIZATION regress_user1;

  CREATE SCHEMA sh;
  CREATE TABLE sh.tt (i INTEGER);

  ALTER TABLE sh.tt REPLICA IDENTITY FULL;

  GRANT USAGE ON SCHEMA sh TO regress_user2;
  GRANT INSERT, SELECT, UPDATE, DELETE, TRUNCATE ON TABLE sh.tt TO regress_user2;
  ));
}

$node_publisher->safe_psql(
	'postgres', qq(
GRANT mdb_replication TO regress_user2;
SET SESSION AUTHORIZATION regress_user1;

CREATE PUBLICATION tap_pub
  FOR TABLE sh.tt;
));


# Delete pg_hba.conf from the given node, add a new entry to it
# and then execute a reload to refresh it.
sub reset_pg_hba
{
	my $node       = shift;
	my $hba_method = shift;

	unlink($node->data_dir . '/pg_hba.conf');
	$node->append_conf('pg_hba.conf', "local all regress_user2 $hba_method");
	$node->append_conf('pg_hba.conf', "local all all trust");
	$node->reload;
	return;
}

# require password for all connection on publisher
reset_pg_hba($node_publisher, 'scram-sha-256');

$ENV{"PGPASSWORD"} = 'regress_lolkekpassword';

$node_subscriber->safe_psql(
	'postgres', qq(
GRANT mdb_admin TO regress_user2;
SET SESSION AUTHORIZATION regress_user2;

CREATE SUBSCRIPTION test_mdb_admin_sub CONNECTION '$publisher_connstr application_name=app_test_mdb_admin_sub user=regress_user2 password=regress_lolkekpassword' PUBLICATION tap_pub WITH(run_as_owner=true);
));

# Wait for initial sync to finish
$node_subscriber->wait_for_subscription_sync($node_publisher, 'app_test_mdb_admin_sub');

# Verify that "regress_admin" can replicate into the tables
#
publish_insert("sh.tt", 2);
publish_insert("sh.tt", 8);
publish_insert("sh.tt", 16);
expect_replication("sh.tt", 3, 2, 16,
	"mdb_admin/mdb_replication role replicates into sh.tt");

# check that no replication possible if permission revoked
$node_subscriber->safe_psql(
		'postgres', qq(
  REVOKE INSERT ON TABLE sh.tt FROM regress_user2
));



publish_insert("sh.tt", 47);

expect_failure(
	"sh.tt",
	3,
	2,
	16,
	qr/ERROR:  permission denied for table tt/,
	"role without INSERT grant for table fails to replicate insert");


# check that no replication possible if permission revoked
$node_subscriber->safe_psql(
		'postgres', qq(
  GRANT INSERT ON TABLE sh.tt TO regress_user2
));


expect_replication("sh.tt", 4, 2, 47,
	"mdb_admin/mdb_replication role replicates after grants again");

publish_update("sh.tt", 2 => 7);
publish_delete("sh.tt", 16);

expect_replication("sh.tt", 3, 7, 47,
	"mdb_admin/mdb_replication role replicates update/delete into sh.tt");

publish_truncate("sh.tt");

publish_insert("sh.tt", 47);

expect_replication("sh.tt", 1, 47, 47,
	"mdb_admin/mdb_replication role replicates truncate sh.tt");

done_testing();
