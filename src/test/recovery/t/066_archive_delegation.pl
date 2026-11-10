# Copyright (c) 2026, PostgreSQL Global Development Group

# The primary keeps an ordered archive frontier while a standby archives the
# newest files.  Missing acknowledgements are an optimization miss, not a wait.
use strict;
use warnings FATAL => 'all';
use PostgreSQL::Test::Cluster;
use PostgreSQL::Test::Utils;
use Test::More;
use Digest::SHA qw(sha256_hex);
use File::Basename qw(basename);
use Time::HiRes qw(time);

my $work = PostgreSQL::Test::Utils::tempdir();
my $helper = "$work/archive.pl";
append_to_file($helper, <<'ARCHIVE');
use strict;
use warnings;
use File::Copy qw(copy);
use File::Compare qw(compare);
my ($control, $log, $archive, $source, $file) = @ARGV;
open(my $input, '<', $control) or die $!;
my ($delay, $fail) = split / /, <$input>;
close($input);
chomp($fail);
exit 1 if $fail;
select(undef, undef, undef, $delay / 1000);
if (-e "$archive/$file")
{
    exit 1 if compare($source, "$archive/$file") != 0;
}
else
{
    copy($source, "$archive/$file") or die $!;
}
open(my $output, '>>', $log) or die $!;
print $output "$file\n";
close($output) or die $!;
ARCHIVE

sub archive_command
{
	my ($control, $log, $archive) = @_;
	my $command = qq{"$^X" "$helper" "$control" "$log" "$archive" %p %f};
	$command =~ s/'/''/g;
	return $command;
}

for my $mode ('success', 'timeout', 'head', 'no_opt_in')
{
	my $archive = "$work/$mode";
	mkdir($archive) or die $!;
	my $primary_control = "$work/${mode}_primary.control";
	my $standby_control = "$work/${mode}_standby.control";
	my $primary_log = "$work/${mode}_primary.copies";
	my $standby_log = "$work/${mode}_standby.copies";
	append_to_file($primary_control, ($mode eq 'head' ? '0' : '100') . " 0\n");
	append_to_file($standby_control,
		($mode eq 'head' ? '1000' : '10') . ' ' . ($mode eq 'timeout' ? '1' : '0') . "\n");
	my $a = PostgreSQL::Test::Cluster->new("primary_$mode");
	$a->init(allows_streaming => 1, extra => ['--wal-segsize' => 1]);
	my $timeout = $mode eq 'timeout' ? 50 : 10000;
	$a->append_conf('postgresql.conf', qq(
archive_mode = on
archive_command = ''
archive_delegate_max_files = 0
archive_delegate_min_backlog = 8
archive_delegate_timeout = $timeout
wal_keep_size = '64MB'
log_min_messages = debug1
));
	$a->start;
	$a->safe_psql('postgres', 'CREATE TABLE delegate_guard (i int)');
	$a->backup('backup');
	my $b = PostgreSQL::Test::Cluster->new("standby_$mode");
	$b->init_from_backup($a, 'backup', has_streaming => 1);
	my $accept = $mode eq 'no_opt_in' ? 'off' : 'on';
	my $standby_command = archive_command($standby_control, $standby_log, $archive);
	$b->append_conf('postgresql.conf', qq(
archive_mode = shared
archive_delegate_accept = $accept
archive_status_report_interval = '60s'
archive_command = '$standby_command'
));
	$b->start;
	for my $i (1 .. 16)
	{
		$a->safe_psql('postgres', "INSERT INTO delegate_guard VALUES ($i); SELECT pg_switch_wal()");
	}
	$a->wait_for_catchup($b);
	is($b->safe_psql('postgres', 'SELECT count(*) FROM delegate_guard'),
		16, "$mode: WAL replay reaches the standby");
	my $status = $a->data_dir . '/pg_wal/archive_status';
	my @files = sort map { basename($_, '.ready') }
	  grep { basename($_) =~ /^[0-9A-F]{24}\.ready$/ } glob("$status/*.ready");
	die 'insufficient backlog' unless @files >= 8;
	my @newest = @files[-4 .. -1];
	my %hash = map { $_ => sha256_hex(slurp_file($a->data_dir . "/pg_wal/$_")) } @files;
	my $primary_command = archive_command($primary_control, $primary_log, $archive);
	$a->append_conf('postgresql.conf', qq(
archive_delegate_max_files = 4
archive_command = '$primary_command'
));
	my $start = time;
	$a->reload;
	if ($mode eq 'success')
	{
		$b->wait_for_log(qr/completed archive delegation batch/);
		ok(!grep(-f "$status/$_.done", @newest),
			'out-of-order acknowledgement leaves newest source files pending');
	}
	my $names = join(',', map { "'$_.ready'" } @files);
	$a->poll_query_until('postgres',
		"SELECT NOT EXISTS (SELECT FROM pg_ls_dir('pg_wal/archive_status') f WHERE f IN ($names))")
	  or die "$mode: primary archive queue did not drain";
	my $elapsed = time - $start;
	my @bad = grep { !-f "$archive/$_" || sha256_hex(slurp_file("$archive/$_")) ne $hash{$_} } @files;
	is_deeply(\@bad, [], "$mode: every archived file matches the source bytes");
	my $local = -f $primary_log ? slurp_file($primary_log) : '';
	if ($mode eq 'success')
	{
		ok(!grep($local =~ /^$_$/m, @newest),
			'acknowledged newest files avoid primary archive callbacks');
	}
	else
	{
		ok(!grep($local !~ /^$_$/m, @newest),
			"$mode: primary archives every unconfirmed newest file itself");
	}
	cmp_ok($elapsed, '<', 8, 'head-of-queue fallback does not wait for the 10s lease')
	  if $mode eq 'head';
	unlike(slurp_file($a->logfile), qr/delegated archive batch/,
		'ordinary physical peer receives no unsolicited task') if $mode eq 'no_opt_in';
	$b->stop;
	$a->stop;
}
done_testing();
