# MDB-48544: Document the actual walsender replication permission behavior
# of this line (14.x).
#
# Verified behavior encoded in this test:
#
# postinit.c gate: a walsender session may start for
#   superuser || has_rolreplication || member of mdb_replication
# (see the "must be superuser, replication role or mdb_replication to start
# walsender" FATAL).  Note: postinit.c has a caching bug
# (`is_mdb_repl_role = role;` stores an OID into a bool), so walsender.c's
# check_mdb_replication() is effectively vacuous on this line: any session
# that passed the startup gate can create LOGICAL replication slots (via a
# database walsender connection, which logical decoding requires anyway).
#
# walsender.c check_permissions() (NO superuser allowance!) rejects
#   START_REPLICATION (slotless and slotful), BASE_BACKUP and physical
#   CREATE_REPLICATION_SLOT for everyone without the REPLICATION attribute,
#   including superusers.  This is the surprising 14-line behavior that this
#   test documents.
#
# This test documents ACTUAL behavior, it does not assert desired behavior.
#
# wal_level is set to logical so that logical CREATE_REPLICATION_SLOT gets
# past CheckLogicalDecodingRequirements() and actually exercises the
# permission checks under test.
#
# Note: when a physical START_REPLICATION command is accepted, the server
# switches to copy-both mode, and plain psql reports
# "unexpected PQresultStatus: 8" and exits.  That psql diagnostic is the
# marker used below to tell "replication actually started" apart from the
# permission errors.

use strict;
use warnings;
use PostgresNode;
use TestLib;
use Test::More tests => 21;

my $node = get_new_node('primary');
$node->init(allows_streaming => 1);
$node->append_conf(
	'postgresql.conf', qq(
wal_level = logical
));
$node->start;

# Roles:
#   r_repl  - has the REPLICATION attribute
#   r_mdb   - member of the mdb_replication role (no REPLICATION attribute)
#   r_plain - plain login role: may not even start a walsender session
#   r_su    - superuser without the REPLICATION attribute
$node->safe_psql('postgres',
	"CREATE ROLE mdb_replication NOLOGIN;");
$node->safe_psql('postgres', "CREATE ROLE r_repl LOGIN REPLICATION;");
$node->safe_psql('postgres', "CREATE ROLE r_mdb LOGIN;");
$node->safe_psql('postgres', "GRANT mdb_replication TO r_mdb;");
$node->safe_psql('postgres', "CREATE ROLE r_plain LOGIN;");
$node->safe_psql('postgres', "CREATE ROLE r_su SUPERUSER LOGIN;");
$node->safe_psql('postgres', "SELECT pg_create_physical_replication_slot('s1');");

# Run one replication-protocol command over a walsender connection.  By
# default a db-less physical walsender connection is used
# ('user=<role> replication=true', no dbname); %opts may override the full
# connection string.  Returns ($ret, $stdout, $stderr).
sub walsender_psql
{
	my ($role, $cmd, %opts) = @_;
	my $connstr = $opts{connstr} // "user=$role replication=true";
	my $stdout  = '';
	my $stderr  = '';
	my $ret     = $node->psql(
		'postgres', $cmd,
		connstr     => $connstr,
		stdout      => \$stdout,
		stderr      => \$stderr,
		on_error_die  => 0,
		on_error_stop => 0);
	return ($ret, $stdout, $stderr);
}

my ($ret, $out, $err);

# The error check_permissions() raises for everyone lacking the REPLICATION
# attribute, superusers included.
my $perm_err = qr/must be superuser or replication role to use replication slots/;

# psql's diagnostic upon entering copy-both mode (accepted
# START_REPLICATION, i.e. replication actually started).
my $stream_started = qr/unexpected PQresultStatus: 8/;

# (a) r_plain cannot start a walsender session at all.
(undef, undef, $err) = walsender_psql('r_plain', 'IDENTIFY_SYSTEM');
like($err,
	qr/must be superuser, replication role or mdb_replication to start walsender/,
	'r_plain is refused to start a walsender session');

# (b) r_repl (REPLICATION attribute) may do everything checked here.
($ret, $out, $err) = walsender_psql('r_repl', 'IDENTIFY_SYSTEM');
is($ret, 0, 'r_repl IDENTIFY_SYSTEM succeeds');
like($out, qr/^\d+\|\d+\|/m, 'r_repl IDENTIFY_SYSTEM returned the system id');

($ret, $out, $err) =
  walsender_psql('r_repl', 'CREATE_REPLICATION_SLOT ps_repl PHYSICAL');
is($ret, 0, 'r_repl physical CREATE_REPLICATION_SLOT succeeds');
like($out, qr/ps_repl/, 'r_repl physical CREATE_REPLICATION_SLOT output');

# Logical slots require a database walsender connection.
($ret, $out, $err) = walsender_psql('r_repl',
	'CREATE_REPLICATION_SLOT tlog_repl LOGICAL pgoutput',
	connstr => 'dbname=postgres user=r_repl replication=database');
is($ret, 0, 'r_repl logical CREATE_REPLICATION_SLOT succeeds');
like($out, qr/tlog_repl/, 'r_repl logical CREATE_REPLICATION_SLOT output');

($ret, $out, $err) = walsender_psql('r_repl',
	'START_REPLICATION 0/0 TIMELINE 1');
like($err, $stream_started,
	'r_repl slotless START_REPLICATION started streaming');
unlike($err, qr/ERROR/, 'r_repl slotless START_REPLICATION has no error');

($ret, $out, $err) = walsender_psql('r_repl',
	'START_REPLICATION SLOT "s1" 0/0 TIMELINE 1');
like($err, $stream_started,
	'r_repl START_REPLICATION SLOT s1 started streaming');
unlike($err, qr/ERROR/, 'r_repl START_REPLICATION SLOT s1 has no error');

# (c) r_mdb (member of mdb_replication) may start a walsender session and run
# IDENTIFY_SYSTEM, but check_permissions() has no mdb_replication allowance.
($ret, $out, $err) = walsender_psql('r_mdb', 'IDENTIFY_SYSTEM');
is($ret, 0, 'r_mdb IDENTIFY_SYSTEM succeeds');
like($out, qr/^\d+\|\d+\|/m, 'r_mdb IDENTIFY_SYSTEM returned the system id');

($ret, $out, $err) = walsender_psql('r_mdb',
	'START_REPLICATION 0/0 TIMELINE 1');
like($err, $perm_err, 'r_mdb slotless START_REPLICATION is rejected');

($ret, $out, $err) = walsender_psql('r_mdb',
	'START_REPLICATION SLOT "s1" 0/0 TIMELINE 1');
like($err, $perm_err, 'r_mdb START_REPLICATION SLOT is rejected');

($ret, $out, $err) = walsender_psql('r_mdb', 'BASE_BACKUP');
like($err, $perm_err, 'r_mdb BASE_BACKUP is rejected');

($ret, $out, $err) = walsender_psql('r_mdb',
	'CREATE_REPLICATION_SLOT ps_mdb PHYSICAL');
like($err, $perm_err, 'r_mdb physical CREATE_REPLICATION_SLOT is rejected');

# De-facto behavior: logical CREATE_REPLICATION_SLOT goes through
# check_mdb_replication(), which is vacuous due to the postinit.c caching bug
# (is_mdb_repl_role stores an OID into a bool), so r_mdb IS allowed.
($ret, $out, $err) = walsender_psql('r_mdb',
	'CREATE_REPLICATION_SLOT tlog_mdb LOGICAL pgoutput',
	connstr => 'dbname=postgres user=r_mdb replication=database');
is($ret, 0, 'r_mdb logical CREATE_REPLICATION_SLOT de-facto succeeds');
like($out, qr/tlog_mdb/, 'r_mdb logical CREATE_REPLICATION_SLOT output');

# (d) A superuser without the REPLICATION attribute: the startup gate lets it
# in (superuser()), but check_permissions() grants NO superuser allowance on
# this line, so START_REPLICATION is rejected even for r_su.
($ret, $out, $err) = walsender_psql('r_su', 'IDENTIFY_SYSTEM');
is($ret, 0, 'r_su IDENTIFY_SYSTEM succeeds');

($ret, $out, $err) = walsender_psql('r_su',
	'START_REPLICATION 0/0 TIMELINE 1');
like($err, $perm_err,
	'r_su (superuser without REPLICATION) is rejected by START_REPLICATION');

$node->stop('fast');
