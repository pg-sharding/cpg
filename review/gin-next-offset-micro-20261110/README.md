# Separate uint16 offset-fragment micro supplement

Large skips improved in the exact extracted fragment; several short skips
regressed substantially. This does not change the main bitmap packet's mixed
and negative SQL screen. The fixed micro is diagnostic evidence, with noisy
short kernels and substantial exact-twin drift, not a clean small-difference
or SQL result.

At n64/skip63, paired kernel CPU changed -56.82% / -51.70%; at n291/skip290,
-87.81% / -87.45%. Negatives include n8/skip4 +45.01% / +51.84%, n8/skip7
+30.58% / +19.68%, and n291/skip4 +15.57% / +31.16%. Exact B/T paired kernel
CPU drift reached -25.40% to +15.61% across cells. The recorded pre/post load
averages were 3.18/1.13/0.55 and 3.22/1.21/0.59. No clean timing-window claim
is made for this micro. All observations and control ranges are retained;
there was no repeat, normalization, trimming, pooling or source tuning.

The fixed design has 15 cells: n8/64/291 and skip0/1/2/4/(n-1), 250,000 calls
per command, B/T/Bitmap, two CPU placements, two warm and six retained rounds
with all six permutations. It completed 720 raw / 540 retained / 180 warm.
The independent auditor checked all 360 absolute groups, 360 pair groups and
2160 direct pairs. The separate smoke completed 45 warm commands/0 retained.

This is an extracted-fragment test with actual PostgreSQL GinScanEntryData
and uint16 offsets. It retains the original page-exhaustion guard and exact
baseline/candidate fragments. Both static wrappers remain in one executable;
B/T use identical selector0 commands, and candidate uses selector1. The common
volatile indirect-call overhead remains. Actual normal ASM was independently
reviewed: a pointer reload/call and offset reset occur inside every one of
the 250,000 iterations. Kernel process CPU/monotonic wall exclude startup and
validation; outer CPU/wall retain them. No database cluster is created here.

The initial compile gate failed before invoking GCC: the harness assumed a
nonexistent include/server path. New r2 obtains both server-header directories
from each installed pg_config, checks containment and 907-header equality.
Production source, fragment C, cases, loops and runner remained byte-identical.
The original failed r1, exact stack, correction diff and root-reviewed r2
normal ASM/status are retained. No production failure is inferred from r1.

* `report/RESULTS.md` shows every CPU/wall cell and twin control.
* `audit/screen-r2/` includes all absolute/pair/direct JSON and TSV statistics.
* `evidence/` retains raw rows, source/header/build bindings, ASM and reviews.
* `replay/` preserves immutable r1/r2 source capsules, separate from production.
* `REPRODUCE.md` explains the main packet prerequisite and a fresh provenance
  binding; `bind-offset-replay.py` never creates a runtime PASS.
* `source/` preserves the unchanged independent production prototype and
  published commit cc5c47d525e01a7eb6af7b6d6fed66fcbde5d7f9 attribution.
* `email-draft-UNSENT.txt` is an English draft, not an email sent to anyone.

The original main bitmap build and ordinary/prefix/lossy qualification are
prerequisites, not replaced by this fragment. Their complete full-AM/SQL
results remain in the separate bitmap packet. C11 and OR heap are independent
alternatives, not composed here. No concurrency or merge claim follows.
The final namespace release proof reports 42 stopped owned cluster lifetimes,
11 unchanged PostgreSQL ELFs, no live owned executable/pidfile/compiler, and
an unchanged micro executable. VM158 was explicitly released to root.

Root independently replayed the complete micro recount and derived tables.
ROOT-REVIEW.json records checks; MANIFEST.json freezes all packet members.
Its new replay-binding helper passed only AST/help and an offline metadata
exercise using historical actual receipts; no second Linux replay ran.
