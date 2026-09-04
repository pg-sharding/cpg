# Copyright (c) 2026, Postgres Professional

use strict;
use warnings FATAL => 'all';

use File::Basename qw(basename dirname);
use File::Copy qw(copy);
use PostgreSQL::Test::Cluster;
use PostgreSQL::Test::Utils;
use Test::More;

sub relation_files
{
	my ($backup, $path) = @_;
	my $directory = dirname("$backup/$path");
	my $filename = basename($path);

	opendir(my $dir, $directory)
	  or die "could not open directory $directory: $!";
	my @files = grep {
		/^\Q$filename\E(?:_(?:fsm|vm|init))?(?:\.\d+)?$/
	} readdir($dir);
	closedir($dir);

	return @files;
}

sub copy_relation_files
{
	my ($source, $destination, $path) = @_;
	my $source_directory = dirname("$source/$path");
	my $destination_directory = dirname("$destination/$path");

	for my $filename (relation_files($source, $path))
	{
		copy("$source_directory/$filename", "$destination_directory/$filename")
		  or die "could not restore $path from trusted storage: $!";
	}

	return;
}

sub slurp_binary
{
	my ($path) = @_;

	open(my $file, '<:raw', $path) or die "could not open $path: $!";
	local $/;
	my $contents = <$file>;
	close($file);

	return $contents;
}

my $node = PostgreSQL::Test::Cluster->new('primary');
$node->init(allows_streaming => 1, extra => ['--wal-segsize=1']);
$node->start;

my $initial_password = 'md511111111111111111111111111111111';
my $changed_password = 'md522222222222222222222222222222222';
my $post_recovery_password = 'md533333333333333333333333333333333';
my $marker = 'ordinary-wal-marker-445566778899';
my $post_recovery_marker = 'ordinary-after-recovery-6677889900';
my $statistic_value = 'classic-statistic-value-7788990011';
my $extended_statistic_value =
	'extended-statistic-value-9900112233:expression-value-0011223344';

$node->safe_psql(
	'postgres', qq{
CREATE ROLE mdb_replication;
CREATE ROLE mdb_admin;
CREATE ROLE backup_user LOGIN;
GRANT mdb_admin TO backup_user;
CREATE ROLE secret_role PASSWORD '$initial_password';
CREATE TABLE payload (value text);
INSERT INTO payload VALUES ('before-backup');
ANALYZE;
CREATE TABLE statistic_payload (value text);
INSERT INTO statistic_payload
SELECT '$statistic_value'
FROM generate_series(1, 100);
CREATE TABLE extended_statistic_payload (a text, b text);
INSERT INTO extended_statistic_payload
SELECT 'extended-statistic-value-9900112233', 'expression-value-0011223344'
FROM generate_series(1, 100);
CREATE STATISTICS statistic_payload_expr
ON ((a || ':' || b)) FROM extended_statistic_payload;
});
$node->safe_psql('postgres',
	'VACUUM FREEZE statistic_payload, extended_statistic_payload;');

my $connstr = $node->connstr('postgres') . ' user=backup_user';
my $repl_connstr = "$connstr replication=1";
my $db_repl_connstr = "$connstr replication=database";

my ($ret, $stdout, $stderr) = $node->psql(
	'postgres', 'IDENTIFY_SYSTEM;',
	extra_params => [ '--dbname' => $repl_connstr ]);
isnt($ret, 0, 'redacted replication is disabled by default');

$node->safe_psql('postgres', q{
ALTER SYSTEM SET ycmdb.redacted_physical_backup = on;
SELECT pg_reload_conf();
});
ok($node->poll_query_until(
	'postgres',
	q{SELECT current_setting('ycmdb.redacted_physical_backup') = 'on';}),
	'redacted physical backup mode is enabled after reload');

($ret, $stdout, $stderr) = $node->psql(
	'postgres', 'IDENTIFY_SYSTEM;',
	extra_params => [ '--dbname' => $repl_connstr ]);
is($ret, 0, 'mdb_admin member can open a redacted replication connection');

($ret, $stdout, $stderr) = $node->psql(
	'postgres', 'SELECT 1 / 0;',
	extra_params => [ '--dbname' => $db_repl_connstr ]);
isnt($ret, 0, 'SQL error closes a database replication connection');
like($stderr, qr/division by zero/, 'SQL error is reported');
is($node->safe_psql('postgres', 'SELECT 1'), '1',
	'SQL error in restricted walsender does not restart the server');

($ret, $stdout, $stderr) = $node->psql(
	'postgres', 'CREATE_REPLICATION_SLOT denied PHYSICAL;',
	extra_params => [ '--dbname' => $repl_connstr ]);
isnt($ret, 0, 'persistent physical slot creation is denied');
like($stderr,
	qr/replication command is not available in redacted physical backup mode/,
	'persistent slot error is reported');

($ret, $stdout, $stderr) = $node->psql(
	'postgres', 'CREATE_REPLICATION_SLOT temporary TEMPORARY PHYSICAL;',
	extra_params => [ '--dbname' => $repl_connstr ]);
is($ret, 0, 'temporary physical slot creation is allowed');

for my $command (
	'CREATE_REPLICATION_SLOT denied TEMPORARY LOGICAL test_decoding;',
	'START_REPLICATION SLOT denied LOGICAL 0/0;',
	'DROP_REPLICATION_SLOT denied;',
	'UPLOAD_MANIFEST;')
{
	($ret, $stdout, $stderr) = $node->psql(
		'postgres', $command,
		extra_params => [ '--dbname' => $repl_connstr ]);
	isnt($ret, 0, "$command is denied");
	like($stderr,
		qr/replication command is not available in redacted physical backup mode/,
		"$command reports the restricted command error");
}

my $backup_fetch = $node->basedir . '/backup_fetch';
$node->command_fails_like(
	[
		'pg_basebackup', '--dbname' => $connstr,
		'--pgdata' => $backup_fetch, '--wal-method=fetch', '--no-sync'
	],
	qr/redacted base backups require WAL streaming/,
	'embedded WAL is denied');

my $paths = $node->safe_psql(
	'postgres', q{
SELECT pg_relation_filepath(oid)
FROM pg_class
WHERE oid IN (
    'pg_authid'::regclass,
    'pg_authid_rolname_index'::regclass,
    'pg_authid_oid_index'::regclass,
    'pg_statistic'::regclass,
    'pg_statistic_relid_att_inh_index'::regclass,
    'pg_statistic_ext_data'::regclass,
    'pg_statistic_ext_data_stxoid_inh_index'::regclass,
    (SELECT reltoastrelid FROM pg_class
     WHERE oid = 'pg_statistic'::regclass),
    (SELECT indexrelid FROM pg_index
     WHERE indrelid = (SELECT reltoastrelid FROM pg_class
                       WHERE oid = 'pg_statistic'::regclass)),
    (SELECT reltoastrelid FROM pg_class
     WHERE oid = 'pg_statistic_ext_data'::regclass),
    (SELECT indexrelid FROM pg_index
     WHERE indrelid = (SELECT reltoastrelid FROM pg_class
                       WHERE oid = 'pg_statistic_ext_data'::regclass)))
ORDER BY 1;
});

my $backup = $node->backup_dir . '/redacted';
$node->command_ok(
	[
		'pg_basebackup', '--dbname' => $connstr,
		'--pgdata' => $backup, '--wal-method=stream', '--checkpoint=fast',
		'--no-sync'
	],
	'redacted base backup');

is(slurp_file("$backup/MDB_REDACTED_BACKUP"),
	"MDB redacted physical backup format 1\n"
	  . "pg_authid, pg_statistic, and pg_statistic_ext_data storage is absent.\n"
	  . "The service must restore those catalogs before PostgreSQL is started.\n",
	'redacted backup marker');

for my $path (split(/\n/, $paths))
{
	is_deeply([ relation_files($backup, $path) ], [],
		"$path is absent from the backup");
}
$node->command_ok([ 'pg_verifybackup', $backup ],
	'redacted backup matches its manifest');

# Simulate the service restoring the omitted catalogs from trusted storage.
$node->safe_psql('postgres', 'CHECKPOINT;');
for my $path (split(/\n/, $paths))
{
	copy_relation_files($node->data_dir, $backup, $path);
}

$node->safe_psql('postgres',
	"SELECT pg_create_physical_replication_slot('redacted_wal', true);");
$node->safe_psql('postgres',
	'ANALYZE statistic_payload; ANALYZE extended_statistic_payload;');
$node->safe_psql(
	'postgres', qq{
ALTER ROLE secret_role PASSWORD '$changed_password';
INSERT INTO payload VALUES ('$marker');
});
$node->safe_psql('postgres', 'SELECT pg_switch_wal();');
$node->safe_psql('postgres',
	"INSERT INTO payload VALUES ('after-first-wal-switch');");
my $endpos =
  $node->safe_psql('postgres', 'SELECT pg_current_wal_flush_lsn();');

my $wal_dir = $node->basedir . '/redacted_wal';
mkdir($wal_dir) or die "could not create directory $wal_dir: $!";
$node->command_ok(
	[
		'pg_receivewal', '--dbname' => $connstr, '--directory' => $wal_dir,
		'--slot=redacted_wal', '--endpos' => $endpos, '--no-loop',
		'--no-sync', '--status-interval=1'
	],
	'continue streaming redacted WAL after the backup');

my @wal_files = sort grep { /^[0-9A-F]{24}$/ } slurp_dir($wal_dir);
ok(scalar(@wal_files) > 0, 'received a complete WAL segment');

my $source_wal = '';
my $redacted_wal = '';
for my $filename (@wal_files)
{
	$source_wal .= slurp_binary($node->data_dir . "/pg_wal/$filename");
	$redacted_wal .= slurp_binary("$wal_dir/$filename");
}

ok(index($source_wal, $changed_password) >= 0,
	'source WAL contains the password verifier');
ok(index($source_wal, $statistic_value) >= 0,
	'source WAL contains a pg_statistic value');
ok(index($source_wal, $extended_statistic_value) >= 0,
	'source WAL contains a pg_statistic_ext_data value');
ok(index($redacted_wal, $changed_password) < 0,
	'redacted WAL does not contain the password verifier');
ok(index($redacted_wal, $statistic_value) < 0,
	'redacted WAL does not contain pg_statistic values');
ok(index($redacted_wal, $extended_statistic_value) < 0,
	'redacted WAL does not contain pg_statistic_ext_data values');
ok(index($redacted_wal, $marker) >= 0,
	'redacted WAL preserves ordinary table data');

$node->command_like(
	[ 'pg_waldump', '--path' => $wal_dir, $wal_files[0], $wal_files[-1] ],
	qr/rmgr: XLOG.*desc: NOOP/s,
	'redacted WAL remains readable');

for my $filename (@wal_files)
{
	copy("$wal_dir/$filename", "$backup/pg_wal/$filename")
	  or die "could not install redacted WAL in restored backup: $!";
}

my $restored = PostgreSQL::Test::Cluster->new('restored');
$restored->init_from_backup($node, 'redacted', has_streaming => 1);
$restored->start;
is($restored->safe_psql('postgres',
		"SELECT rolpassword FROM pg_authid WHERE rolname = 'secret_role';"),
	$initial_password, 'redacted WAL does not change pg_authid during replay');
is($restored->safe_psql('postgres',
		"SELECT count(*) FROM payload WHERE value = '$marker';"),
	'1', 'ordinary WAL is replayed from the redacted stream');

my $restored_connstr =
  $restored->connstr('postgres') . ' user=backup_user';
my $restored_repl_connstr = "$restored_connstr replication=1";
($ret, $stdout, $stderr) = $restored->psql(
	'postgres', 'IDENTIFY_SYSTEM;',
	extra_params => [ '--dbname' => $restored_repl_connstr ]);
isnt($ret, 0, 'redacted replication is denied during backup recovery');
like($stderr, qr/cannot start a redacted WAL sender during recovery/,
	'recovery restriction is reported');

$restored->promote;
($ret, $stdout, $stderr) = $restored->psql(
	'postgres', 'IDENTIFY_SYSTEM;',
	extra_params => [ '--dbname' => $restored_repl_connstr ]);
is($ret, 0, 'redacted replication is available after promotion');
($ret, $stdout, $stderr) = $restored->psql(
	'postgres', 'TIMELINE_HISTORY 2;',
	extra_params => [ '--dbname' => $restored_repl_connstr ]);
is($ret, 0, 'redacted replication can read promoted timeline history');

$restored->safe_psql('postgres',
	"SELECT pg_create_physical_replication_slot('after_recovery', true);");
$restored->safe_psql(
	'postgres', qq{
ALTER ROLE secret_role PASSWORD '$post_recovery_password';
INSERT INTO payload VALUES ('$post_recovery_marker');
});
$restored->safe_psql('postgres', 'SELECT pg_switch_wal();');
$restored->safe_psql('postgres',
	"INSERT INTO payload VALUES ('after-recovery-wal-switch');");
my $post_recovery_endpos =
  $restored->safe_psql('postgres', 'SELECT pg_current_wal_flush_lsn();');
my $post_recovery_wal_dir = $restored->basedir . '/redacted_wal';
mkdir($post_recovery_wal_dir)
  or die "could not create directory $post_recovery_wal_dir: $!";
$restored->command_ok(
	[
		'pg_receivewal', '--dbname' => $restored_connstr,
		'--directory' => $post_recovery_wal_dir,
		'--slot=after_recovery', '--endpos' => $post_recovery_endpos,
		'--no-loop', '--no-sync', '--status-interval=1'
	],
	'continue redacted streaming after backup recovery');

my $post_recovery_redacted_wal = '';
for my $filename (
	sort grep { /^[0-9A-F]{24}$/ } slurp_dir($post_recovery_wal_dir))
{
	$post_recovery_redacted_wal .=
	  slurp_binary("$post_recovery_wal_dir/$filename");
}
ok(index($post_recovery_redacted_wal, $post_recovery_password) < 0,
	'post-recovery stream omits the password verifier');
ok(index($post_recovery_redacted_wal, $post_recovery_marker) >= 0,
	'post-recovery stream preserves ordinary WAL');
$restored->stop;

my $continuation_password = 'md512345678901234567890123456789012';
my $continuation_password_payload = substr($continuation_password, 3);
my $continuation_marker = 'ordinary-after-continuation-1122334455';
$node->safe_psql('postgres', 'CHECKPOINT;');
my $auth_record_lsns = $node->safe_psql(
	'postgres', qq{
BEGIN;
DO \$\$
BEGIN
    IF mod(pg_wal_lsn_diff(pg_current_wal_insert_lsn(), '0/0')::bigint,
           1048576) >= 1046500 THEN
        PERFORM pg_switch_wal();
    END IF;
    WHILE mod(pg_wal_lsn_diff(pg_current_wal_insert_lsn(), '0/0')::bigint,
              1048576) < 1046500 LOOP
        INSERT INTO payload VALUES (repeat('p', 500));
    END LOOP;
END;
\$\$;
SELECT pg_current_wal_insert_lsn();
ALTER ROLE secret_role PASSWORD '$continuation_password';
SELECT pg_current_wal_insert_lsn();
COMMIT;
});
my ($auth_record_start, $auth_record_end) = split(/\n/, $auth_record_lsns);
isnt(
	$node->safe_psql(
		'postgres',
		"SELECT pg_walfile_name('$auth_record_start'::pg_lsn) = "
		  . "pg_walfile_name('$auth_record_end'::pg_lsn);"),
	't', 'pg_authid WAL record crosses a segment boundary');

$node->safe_psql('postgres',
	"SELECT pg_create_physical_replication_slot('redacted_continuation', true);");
$node->safe_psql('postgres',
	"INSERT INTO payload VALUES ('$continuation_marker');");
$node->safe_psql('postgres', 'SELECT pg_switch_wal();');
$node->safe_psql('postgres',
	"INSERT INTO payload VALUES ('after-continuation-wal-switch');");
my $continuation_endpos =
  $node->safe_psql('postgres', 'SELECT pg_current_wal_flush_lsn();');

my $continuation_dir = $node->basedir . '/redacted_continuation';
mkdir($continuation_dir)
  or die "could not create directory $continuation_dir: $!";
$node->command_ok(
	[
		'pg_receivewal', '--dbname' => $connstr,
		'--directory' => $continuation_dir,
		'--slot=redacted_continuation', '--endpos' => $continuation_endpos,
		'--no-loop', '--no-sync', '--status-interval=1'
	],
	'redact a WAL record that starts before the requested segment');

my @continuation_files =
  sort grep { /^[0-9A-F]{24}$/ } slurp_dir($continuation_dir);
my $continuation_source_wal = '';
my $continuation_redacted_wal = '';
for my $filename (@continuation_files)
{
	$continuation_source_wal .=
	  slurp_binary($node->data_dir . "/pg_wal/$filename");
	$continuation_redacted_wal .=
	  slurp_binary("$continuation_dir/$filename");
}
ok(index($continuation_source_wal, $continuation_password_payload) >= 0,
	'source continuation contains the password verifier payload');
ok(index($continuation_redacted_wal, $continuation_password_payload) < 0,
	'redacted continuation omits the password verifier payload');
ok(index($continuation_redacted_wal, $continuation_marker) >= 0,
	'ordinary WAL after the continuation is preserved');

$node->backup('standby_backup');
my $standby = PostgreSQL::Test::Cluster->new('standby');
$standby->init_from_backup($node, 'standby_backup', has_streaming => 1);
$standby->start;

is($node->safe_psql('postgres',
		"SELECT pg_relation_filenode('pg_authid_rolname_index');"),
	'2676', 'pg_authid index has its bootstrap relfilenumber');
$node->safe_psql('postgres',
	'BEGIN; REINDEX INDEX pg_authid_rolname_index; ROLLBACK;');
is($node->safe_psql('postgres',
		"SELECT pg_relation_filenode('pg_authid_rolname_index');"),
	'2676', 'aborted rewrite restores the bootstrap relfilenumber');
ok(-e $node->data_dir . '/MDB_REDACTED_BACKUP_DISABLED',
	'aborted rewrite permanently disables the redacted format');
$node->safe_psql('postgres', 'SELECT pg_switch_wal();');
$node->wait_for_replay_catchup($standby);
ok(-e $standby->data_dir . '/MDB_REDACTED_BACKUP_DISABLED',
	'disablement is replayed on a standby');
($ret, $stdout, $stderr) = $node->psql(
	'postgres', 'IDENTIFY_SYSTEM;',
	extra_params => [ '--dbname' => $repl_connstr ]);
isnt($ret, 0, 'redacted replication is denied after attempted pg_authid rewrite');
like($stderr,
	qr/cannot start a redacted WAL sender after sensitive catalog storage has been rewritten/,
	'permanent disablement is reported');

my $standby_repl_connstr =
  $standby->connstr('postgres') . ' user=backup_user replication=1';
$standby->promote;
($ret, $stdout, $stderr) = $standby->psql(
	'postgres', 'IDENTIFY_SYSTEM;',
	extra_params => [ '--dbname' => $standby_repl_connstr ]);
isnt($ret, 0, 'replayed disablement rejects redacted replication after promotion');
like($stderr,
	qr/cannot start a redacted WAL sender after sensitive catalog storage has been rewritten/,
	'replayed disablement is reported after promotion');

my $rewrite_node = PostgreSQL::Test::Cluster->new('rewrite');
$rewrite_node->init(allows_streaming => 1);
$rewrite_node->append_conf('postgresql.conf',
	'ycmdb.redacted_physical_backup = on');
$rewrite_node->start;
$rewrite_node->safe_psql(
	'postgres', q{
CREATE ROLE mdb_replication;
CREATE ROLE mdb_admin;
CREATE ROLE backup_user LOGIN;
GRANT mdb_admin TO backup_user;
ANALYZE;
});
my $old_statistic_relfilenode = $rewrite_node->safe_psql(
	'postgres', "SELECT pg_relation_filenode('pg_catalog.pg_statistic');");
$rewrite_node->safe_psql('postgres',
	'VACUUM FULL pg_catalog.pg_statistic;');
isnt(
	$rewrite_node->safe_psql(
		'postgres', "SELECT pg_relation_filenode('pg_catalog.pg_statistic');"),
	$old_statistic_relfilenode,
	'VACUUM FULL rewrites pg_statistic storage');
ok(-e $rewrite_node->data_dir . '/MDB_REDACTED_BACKUP_DISABLED',
	'pg_statistic rewrite permanently disables the redacted format');

my $rewrite_repl_connstr =
  $rewrite_node->connstr('postgres') . ' user=backup_user replication=1';
($ret, $stdout, $stderr) = $rewrite_node->psql(
	'postgres', 'IDENTIFY_SYSTEM;',
	extra_params => [ '--dbname' => $rewrite_repl_connstr ]);
isnt($ret, 0, 'redacted replication is denied after pg_statistic rewrite');
like($stderr,
	qr/cannot start a redacted WAL sender after sensitive catalog storage has been rewritten/,
	'pg_statistic rewrite disablement is reported');

done_testing();
