# GiST BOX followups: complete results

Both prototypes are implemented, built and measured. **C is not selected;
D is a limited dense-page candidate, not a general replacement for V2r2.**
All results use exact B72 `72b9498df9a369e747f8d96efb5a6cd33c2451e2`,
not current upstream master. R is unchanged V2r2. C and D are independent
alternatives above R, not a patch series.

Numbers separated by `/` refer to cohort 0 / cohort 1. Effects are medians
of ten direct same-round percentages, not ratios of absolute medians.
Negative means less time. No observations were trimmed or normalized, and
cohorts were not pooled.

| Scenario | C/R | D/R |
|---|---:|---:|
| SQL forced all-match | −0.85% / +3.09% | **−1.83% / −2.99%** |
| SQL natural all-match | −1.68% / +0.60% | −3.63% / −1.95% |
| SQL sparse join | +1.27% / +1.71% | **+10.42% / −3.43%** |
| SQL NULL control | +0.45% / +10.87% | −1.60% / −0.33% |
| Actual-AM sparse micro CPU | +0.37% / −1.12% | −1.29% / −5.11% |
| Actual-AM all-match micro CPU | −1.15% / +2.17% | −1.23% / −0.49% |

The forced all-match R/D absolute execution medians are 20.6335/20.2810 ms
and 23.7375/21.6990 ms. Direct D/R ranges are −12.55..+6.13% and
−37.83..+76.04%, crossing zero in both cohorts. Whole-command CPU effects are
−1.78% / −2.79%, with similarly broad ranges. These are promising median
changes, not a statistically established general regression repair.

D retains the shared batching prototype's sparse SQL benefit against B:
−40.53% / −41.14%; B/D medians are 5.0765/3.0725 ms and
5.8240/4.1580 ms. That large gain already exists in R and must not be credited
to this incremental continuation change. Against R, D's sparse SQL ranges
are −12.73..+42.20% and −32.16..+72.70%; whole-command CPU is +9.84% / −3.56%.
The two cohorts therefore do not establish a uniform sparse improvement.

Controls limit attribution. D/R sequential SQL effects are −8.00% / +1.48%,
although the query uses no GiST scan. D/B sequential SQL in cohort 1 is +3.55%
with all ten pairs positive (+1.50..+6.72%). The exact B twin differs from B
by −0.83% / −8.25% on forced all-match and +14.41% / 0.00% on tiny-forced.
Do not subtract these movements from candidate effects or invent a cause.
C's NULL SQL cost in cohort 1 is +10.87% against R, with CPU +10.44%; it
does not demonstrate the intended general offpath repair.

All-match natural and forced cases both actually used Index Only Scan on
boxes_gist, returning 199,802 rows. Sparse joins used 512 actual index loops;
the sequential control actually used Seq Scan. Plans and complete raw
observations remain available. The actual-AM micro calls the real bitmap
scan API, so its primary process-CPU interval differs from SQL execution and
from the old extracted page-loop model.

## Validation and provenance

Six full clean builds at common paths passed original core239: B/R/C/D release
and C/D assert. GCC 13.3, −O2 −g −fno-lto, OpenSSL, no ICU/readline, j2/nice10.
The added C bool fits padding at offset 34: scan-state size remains 24,664
bytes, distances offset 40 and pageData offset 72 in every installed layout.

Finite qualification passed 132 complete ordered multiset comparisons against
B's forced-sequential references, 96 original SQL case checks, 24 actual-AM
TID-count checks, prepared rescans, forced bitmap/projection and zero-key
coverage across all six backends. This is finite coverage, not a concurrency,
all-platform or production-workload proof.

The accepted r2 campaign has **2,400 raw / 2,000 retained / 400 warm**
observations: 16 unchanged SQL cases and four prospective actual-AM micros,
five roles B/exact B twin/R/C/D, two fresh process cohorts. Ten-row Williams
orders balance every position and ordered adjacency. All copies are created,
hashed and fsynced before role assignment; cohort two reverses case/slot/CPU
placement. Every timed backend has the same validation history. This is one
shared VM158, not independent hardware replication.

An independent manual-formula recount checked 28,800 numeric values and the
key/order bindings; maximum floating difference was 2.84e−14. Local replay
also passes and produces byte-identical summary Markdown. Original Linux
results remain authoritative; local analysis is not another Linux run.

Failed diagnostic preparation is retained separately. The first micro compile
used an obsolete API signature; corrected preflight passed −Werror. The first
matrix harness overwrote native-result JSON with Boolean metadata and stopped
on its first warm record: one raw warm observation, zero accepted observations.
r2 changes only that metadata name and namespaces, uses fresh copies and its
own 100-command smoke. Production source, cases, clock boundaries and planned
sample counts are unchanged. Neither failed attempt is pooled into r2.

Final read-only checks found all 37 owned data directories shut down, all
64 recorded runtime postmaster/backend PIDs absent and no owned sockets.
All six installations, the 7,726-file source tree, canonical seed, frozen
runtime scripts and module remained unchanged. Thirty-two runtime clusters
were started across qualification, both smokes, failed r1 and accepted r2;
the five unused r1 cohort-1 copies were never started. Foreign services were
untouched; VM84 received preparation files only.

## Artifacts and next decision

[All absolute ranges and three metric boundaries](results/ALL-RESULTS.md),
CSV exports and all ten direct pairs accompany complete raw observations.
[Reproduction](REPRODUCE.md) includes source/build flags, deterministic setup,
micro/SQL commands and the exact executed drivers. CREATE INDEX is setup,
not a measured acceleration target. Email remains an English UNSENT draft.

Source branches are published and verified:

- [C: rescan gate](https://github.com/pg-sharding/cpg/tree/experiments/gist-box-rescan-gate-b72-20261109),
  `69418cd771db8d58888fa8184dad583bda2ce30a`.
- [D: dense continuation](https://github.com/pg-sharding/cpg/tree/experiments/gist-box-dense-continuation-b72-20261109),
  `c5fa668c594cb3b2195f858bf5aa2118e5d6733d`.

These are exact source identities for the frozen alternatives; original build
receipts retain their historical null Git-commit fields. Both commits have
V2r2 parent `ebd53d036faaece35a56139abe24641496affbe6`.

The contribution is a measured implementation tradeoff in scalar conservative
BOX rejection. Query/scan eligibility caching and spatial batching have prior
context; no new algorithm or exhaustive novelty claim is made. No new mail
archive or current CommitFest search was performed in this step.
