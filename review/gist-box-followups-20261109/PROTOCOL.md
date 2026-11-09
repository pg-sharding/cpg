# Independent BOX followups to V2r2

Baseline B72: `72b9498df9a369e747f8d96efb5a6cd33c2451e2`.
R is exact historical V2r2, gistget.c SHA256
`0af264c406f4d61c8ed91011fb7ba44f46b2be9748c0350eb03909f432ea4dea`.
C caches only necessary caller eligibility at every rescan; full semantic
helper validation remains. D resumes the generic page loop after eight valid
BOX sample tuples all pass. C/D are independent alternatives, not a series.
No batch-size, sample-size, minimum-page-size or GUC tuning is planned.

Build six complete backends at common source/build/compiled-prefix paths:
B/R/C/D release, C/D assert. GCC -O2 -g -fno-lto, no ICU/readline, OpenSSL,
j2/nice10. Original core239 must pass for each without expected changes.
Run full header-dependent rebuilds, inspect normal gistget/gistscan objects
and actual GISTScanOpaqueData size/field offsets. Existing runtimes and all
historical experiments remain unchanged.

Reuse the historical deterministic BOX setup and all 16 SQL case texts and
their settings. The forwarding custom-opclass module must be an explicit new
dependency, loaded equally in every tested backend. Build one fresh canonical
seed with B and create every numbered copy before assigning code roles.
Validate complete ordered result multisets against B's forced sequential
reference, prepared rescans, zero/two-key, custom/point/KNN/NULL, float edge,
index-only reconstruction, and forced bitmap output. Inspect actual plans.
Qualification and smoke precede accepted observations; failed attempts have
new output directories and contribute no accepted observations.

The fresh microbenchmark calls the real index_rescan/index_getbitmap API on
the real index, including scan-key replacement, page traversal, ordinary
callbacks and bitmap creation/free. Its process-CPU interval excludes initial
relation/scan/query setup. It is not the old extracted page-loop model and
must not be numerically pooled with that model. Sparse, medium, absent and
all-match queries are fixed before timings. Check returned TID counts against
separate ordinary SQL answers outside its process-CPU interval.

Five release roles B/exact B twin/R/C/D, two fresh process cohorts on one VM.
Four micro and 16 SQL cases, two warm plus ten retained rounds, continuous
10-row Williams scheduling for five roles: 2,400 raw / 2,000 retained / 400
warm observations. Each retained role occupies every position twice and every
ordered role adjacency appears twice per retained case. Preserve all ten
direct role pairs, absolute min/median/max, MAD and sample standard deviation.
No trimming, control normalization, cohort pooling or timing-driven repetition.

SQL primary is EXPLAIN Execution Time with TIMING OFF; full BUFFERS/WAL plans
remain. Whole-command backend schedstat CPU, runqueue, physical I/O and client
wall are separately reported. Literal answers execute after the EXPLAIN,
outside its interval. Identical validation history for timed backends. Keep
natural sequential controls and forced index controls distinct. Record code
identities, process birth/affinity/mappings and shared VM load. A shared VM
does not provide independent hardware replication or layout causality.

Run only on the two authorized build VMs. The archive VM is not used. Do not
stop foreign processes or change system settings to improve measurements.
Stop every owned cluster in finally and verify PID/socket absence and
unchanged source/installed inputs. Preserve patches, English UNSENT drafts,
all negatives, source/config/setup/replay instructions, then publish to
separate cpg experimental branches and the internal S3 prefix without deletes.
