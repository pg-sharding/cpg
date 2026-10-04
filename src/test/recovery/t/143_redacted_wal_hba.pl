# Copyright (c) 2026, Postgres Professional

# Test that redacted physical backup walsender connections are not gated
# by the database column of pg_hba.conf.  A member of mdb_replication
# without the REPLICATION attribute must be able to connect even if
# pg_hba.conf contains no "replication" record, provided
# ycmdb.redacted_physical_backup is enabled.  Other roles (superusers,
# REPLICATION roles, or plain mdb_replication members with the GUC
# disabled) must still be rejected by such an HBA configuration.

use strict;
use warnings FATAL => 'all';

use PostgreSQL::Test::Cluster;
use PostgreSQL::Test::Utils;
use Test::More;

# ---------------------------------------------------------------------------
# Setup: a primary node whose pg_hba.conf has no "replication" records.
# ---------------------------------------------------------------------------
my $node = PostgreSQL::Test::Cluster->new('primary');
$node->init(allows_streaming => 1);

# Rewrite pg_hba.conf while the server is down, removing every
# "replication" record added by initdb, so that a physical walsender has
# no matching database record.
{
	my $hba = $node->data_dir . '/pg_hba.conf';
	open(my $fh, '<', $hba) or die "could not open $hba: $!";
	my @lines = <$fh>;
	close($fh);
	open(my $out, '>', $hba) or die "could not open $hba: $!";
	for my $line (@lines)
	{
		next if $line =~ /^\s*(local|host\S*)\s+replication\s/;
		print $out $line;
	}
	close($out);
}

$node->start;

$node->safe_psql('postgres', qq{
CREATE ROLE mdb_replication;
CREATE ROLE backup_user LOGIN;
GRANT mdb_replication TO backup_user;
});

my $connstr = $node->connstr('postgres');

# ---------------------------------------------------------------------------
# With no "replication" HBA record even a superuser cannot start a
# physical replication connection.
# ---------------------------------------------------------------------------
my ($ret, $stdout, $stderr) = $node->psql(
	'postgres', 'IDENTIFY_SYSTEM;',
	extra_params => ['--dbname' => "$connstr user=postgres replication=1"]);
isnt($ret, 0, 'superuser rejected without replication hba record');
like($stderr, qr/no pg_hba\.conf entry for replication connection/,
	'replication hba rejection is reported');

# Ditto for a mdb_replication member while the GUC is off.
($ret, $stdout, $stderr) = $node->psql(
	'postgres', 'IDENTIFY_SYSTEM;',
	extra_params => ['--dbname' => "$connstr user=backup_user replication=1"]);
isnt($ret, 0, 'mdb_replication member rejected while GUC is off');
like($stderr, qr/no pg_hba\.conf entry for replication connection/,
	'GUC-off rejection is reported');

# ---------------------------------------------------------------------------
# Enable redacted physical backup: now the mdb_replication member must
# pass the HBA check (the database column check is skipped for it).
# ---------------------------------------------------------------------------
$node->safe_psql('postgres', q{
ALTER SYSTEM SET ycmdb.redacted_physical_backup = on;
SELECT pg_reload_conf();
});
ok($node->poll_query_until(
	'postgres',
	q{SELECT current_setting('ycmdb.redacted_physical_backup') = 'on';}),
	'redacted physical backup mode enabled');

($ret, $stdout, $stderr) = $node->psql(
	'postgres', 'IDENTIFY_SYSTEM;',
	extra_params => ['--dbname' => "$connstr user=backup_user replication=1"]);
is($ret, 0, 'redacted walsender passes HBA without replication record');
like($stdout, qr/^\d+\|1\|/, 'IDENTIFY_SYSTEM succeeded');

# Normal (non-replication) sessions of the same user still work: the
# regular HBA rules still apply to them.
$ret = $node->psql('postgres', 'SELECT 1;',
	extra_params => ['--dbname' => "$connstr user=backup_user"]);
is($ret, 0, 'normal sessions of backup_user still pass HBA');

# A superuser is still gated: has_rolreplication() is true for it, so
# the HBA bypass does not apply.
($ret, $stdout, $stderr) = $node->psql(
	'postgres', 'IDENTIFY_SYSTEM;',
	extra_params => ['--dbname' => "$connstr user=postgres replication=1"]);
isnt($ret, 0, 'superuser still rejected without replication hba record');

# A role with the REPLICATION attribute is gated as well, even though it
# is also a member of mdb_replication.
$node->safe_psql('postgres', q{
CREATE ROLE repl_user LOGIN REPLICATION;
GRANT mdb_replication TO repl_user;
});
($ret, $stdout, $stderr) = $node->psql(
	'postgres', 'IDENTIFY_SYSTEM;',
	extra_params => ['--dbname' => "$connstr user=repl_user replication=1"]);
isnt($ret, 0, 'role with REPLICATION attribute still rejected');

done_testing();
