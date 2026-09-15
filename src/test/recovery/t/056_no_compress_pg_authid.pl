
# Copyright (c) 2026, PostgreSQL Global Development Group

# Test that full-page images of pg_authid are never compressed, even when
# wal_compression is enabled.
#
# pg_authid stores role passwords inline in its tuples (it has no TOAST
# table), so a compressed FPI would leak information about the password
# material via the compressed image length, like in the attack described in:
# https://www.postgresql.org/message-id/552E0F78.10409%40iki.fi
#
# The test verifies that:
# 1. A modification of pg_authid after a checkpoint produces an uncompressed
#    FPI, even with wal_compression = pglz.
# 2. FPI compression still works for other relations (a control table with
#    highly compressible contents must produce a compressed FPI).

use strict;
use warnings FATAL => 'all';
use IPC::Run;
use PostgreSQL::Test::Cluster;
use PostgreSQL::Test::Utils;
use Test::More;

my $node = PostgreSQL::Test::Cluster->new('primary');
$node->init;
$node->append_conf('postgresql.conf', 'wal_compression = pglz');
$node->start;

# Fill pg_authid's first page with many roles, so that the page is well
# packed (small hole) and its content is repetitive enough to compress well.
# This ensures the test can detect a regression to "FPI gets compressed":
# with compression enabled, the FPI of the next modification of this page
# would be much smaller than an uncompressed one.
my $fill_roles = join "\n",
  map { "CREATE ROLE regress_filler$_ PASSWORD 'secret';" } 1 .. 100;
$node->safe_psql('postgres', "SET password_encryption = md5;\n$fill_roles");

# Control table with highly compressible contents.  Its FPI must be
# compressed, proving that wal_compression is in effect and that the
# no-compression logic only applies to pg_authid.  A row is inserted
# beforehand so that the post-checkpoint insert modifies an existing page
# (an insert into a brand-new page uses REGBUF_WILL_INIT and produces no
# full-page image at all).
$node->safe_psql('postgres',
	q{CREATE TABLE compressme (t text); INSERT INTO compressme VALUES (repeat('y', 1000));}
);
my $filepath =
  $node->safe_psql('postgres', 'SELECT pg_relation_filepath(\'compressme\')');
my ($dbid, $relfilenode) = $filepath =~ m{^base/(\d+)/(\d+)$};
ok(defined $relfilenode, "got control table location: $filepath");

# Take a checkpoint, so that the next modification of each page produces a
# full-page image.
$node->safe_psql('postgres', 'CHECKPOINT');
my $lsn_before = $node->safe_psql('postgres', 'SELECT pg_current_wal_lsn()');

# Modify pg_authid.  The heap update produces an FPI of the pg_authid page,
# which must not be compressed even though the page content would compress
# well.
$node->safe_psql('postgres',
	q{ALTER ROLE regress_filler1 PASSWORD 'guess12345'});
my $wal_bytes_authid = $node->safe_psql('postgres', qq{
	SELECT pg_wal_lsn_diff(pg_current_wal_lsn(), '$lsn_before');
});
my $lsn_mid = $node->safe_psql('postgres', 'SELECT pg_current_wal_lsn()');

# Modify the control table.  Its FPI should be compressed.
$node->safe_psql('postgres', "INSERT INTO compressme VALUES (repeat('x', 1000))"
);
my $wal_bytes_control = $node->safe_psql('postgres', qq{
	SELECT pg_wal_lsn_diff(pg_current_wal_lsn(), '$lsn_mid');
});
my $lsn_after = $node->safe_psql('postgres', 'SELECT pg_current_wal_lsn()');

# The uncompressed FPI of a well-packed pg_authid page must dominate the WAL
# volume of the ALTER ROLE, so it should be close to BLCKSZ.  A compressed
# FPI of the repetitive page would be far smaller.
cmp_ok($wal_bytes_authid, '>', 7000,
	'ALTER ROLE WAL volume is close to an uncompressed page image');

# Conversely, the control insert's FPI is compressed, so its WAL volume must
# be much smaller than a page.
cmp_ok($wal_bytes_control, '<', 4000,
	'control insert WAL volume is far below an uncompressed page image');

# Dump the WAL records written by both modifications, with block details,
# and inspect the FPIs.
my $stdout = '';
my $stderr = '';
my $result = IPC::Run::run [
	'pg_waldump', '--bkp-details',
	'--path', $node->data_dir . '/pg_wal',
	'-s', $lsn_before, '-e', $lsn_after ],
	'>', \$stdout, '2>', \$stderr;
ok($result, 'pg_waldump succeeded');
is($stderr, '', 'pg_waldump without warnings');

# Check the pg_authid FPI: it must be present and uncompressed.  pg_authid
# is a shared catalog, so its block reference is "rel 1664/0/1260".
my @authid_lines =
  grep { /rel 1664\/0\/1260/ && /FPW/ } split(/\n/, $stdout);
ok(scalar(@authid_lines) >= 1, 'pg_authid full-page image was logged');
for my $line (@authid_lines)
{
	unlike($line, qr/compression saved/,
		"pg_authid FPI is not compressed: $line");
}

# Check the control table FPI: it must be compressed with pglz.
my @control_lines =
  grep { /rel 1663\/$dbid\/$relfilenode/ && /FPW/ } split(/\n/, $stdout);
ok(scalar(@control_lines) >= 1, 'control table full-page image was logged');
for my $line (@control_lines)
{
	like($line, qr/compression saved: \d+, method: pglz/,
		"control table FPI is compressed: $line");
}

$node->stop;
done_testing();
