# C11: full builds, ordinary correctness and a bounded GIN screen

C11 retains the combined C9 benefits against fixed B, but it does not show a
consistent improvement over C10. The full-scan AM loop regressed against C10
by **5.93% and 0.28%** in the two placements. The SQL Seq control was **5.27%
slower than B** in the second placement. All controls and negative results
are retained; this packet makes no universal upgrade recommendation.

Five fresh builds passed all 239 core regression tests and the posting-list
test: B, C9, C10 and C11 release, plus C11 with assertions. Ordinary
qualification passed all 25 SQL cases on each build, 40 prepared checks and
35 actual AM checks. The screen then completed **2,400 raw / 2,000 retained /
400 warm observations**, covering 13 SQL cases and 7 actual AM cases, with
five roles and two placements. B and T use the exact same baseline executable.

The independent recount verified 670 absolute groups, 1,340 pair groups and
13,400 direct pairs. Plan shapes, actual rows and loops matched within every
case and placement. Retained SQL and backend I/O counters were zero. All
16 qualification and screen clusters stopped cleanly. These are finite,
serial, synthetic checks; they are not concurrency or general merge
qualification.

This is an assembled review packet, not a new measurement. The actual runs
were on VM158 in the recorded namespace. The portable commands below and the
`--git` input alternative have not undergone a new Linux replay. Offline raw
restoration, recount and rendering are checked separately.

## Read the evidence

- `screen-report-r2/RESULTS.md`: every case, paired percentages and limits.
- `screen-report-r2/absolute.tsv`: CPU, client wall, executor and AM clocks,
  with min, median, max, mean, sample SD and MAD.
- `screen-report-r2/pairs.tsv` and `direct-pairs.tsv`: all role pairs.
- `raw-chunks/`: whole-line gzip chunks restoring the exact original JSONL.
- `screen-evidence-r1/`: plans, role and executable bindings, analyses,
  workload oracles, source/install checks and all screen stop proofs.
- `evidence-r1/`: five build receipts, source/header/object inventories,
  normal production ASM and ordinary qualification proofs. Complete runner
  logs, executables and PGDATA are excluded.
- `independent-screen-r1/`, `C11-QUALIFICATION-LOCAL-RECOUNT.json` and
  `CLEANUP-SUMMARY.json`: independent recounts and cleanup summary.
- `email-draft-UNSENT.txt`: an English draft; no mail was sent.

The frozen preparation manifests under `c11/` originally said “not executed”.
They identify the bytes prepared before execution. Actual PASS receipts and
results above establish what subsequently ran. Those original inputs are
preserved unchanged, including their original wording.

## Source alternatives

Raw B72 is `72b9498df9a369e747f8d96efb5a6cd33c2451e2`. Fixed B is
`8a8c475037bfde101da23cc9b0364c9c020eca93`; C9 is
`0ab3bd65c8957ea5e25f9ef8981401f0616d99de`; C10 is
`cf6df20681101bc58dcb5cf47d3fafd738aaa458`; C11 is
`ca6ad39111cd67f20ff2dd3a8f619239d0360a10`.

`c11/code-over-fixed-B.diff` is the complete C11 alternative over fixed B.
`c11/C11-over-C10.patch` and `.diff` are the exact incremental change over
C10. Do not stack the standalone diff on C9 or C10. The build source plan
reconstructs each comparison tree independently from B72 and verifies every
one of its 7,726 source files. The common prerequisite is identical and
outside this performance experiment.

C11 keeps the bounded BlockId load while restoring the original logical
`block << 32 | offset` comparison-key values. It keeps the six-byte TID and
two-byte alignment. The general comparison/deferred-decoding directions were
discussed by [Heikki Linnakangas in 2014](https://www.postgresql.org/message-id/52F373CC.4050800%40vmware.com).
This packet makes no novelty claim. Historical publication receipts are
preserved under `source-publication-historical/`; their test status reflects
that earlier publication, not this later run.

## Repeat the build and screen

See [REPRODUCE.md](REPRODUCE.md). The baseline archive is deliberately omitted;
use an existing local PostgreSQL Git repository containing exact B72 with the
supported `--git` option. The driver leaves its worktree and HEAD unchanged.
The actual experiment used the same frozen driver with the archived B72
input. Every source snapshot, setup query, answer and AM module needed for a
new run is included here.

The full 25-case timing matrix was not run. CREATE INDEX, INSERT, VACUUM,
larger/restart-cache and second-host results are outside this packet. Bitmap
offset and heap prototypes are independent experiments and their results are
not included. No trimming, control normalization, pooled placements or
selective rerun was used.

## Preserved negatives

`negatives/` records two local source-proof setup errors, a derived table
renderer error and a later artifact-name collision. The collision affected
transfer archive names after the C11 screen; the original C11 archive and
receipt were restored byte-for-byte and all executed C11 input hashes
verified. It did not change source, executable or measurement bytes. These
are preparation/transport events, not candidate SQL failures.

`MANIFEST.json` lists SHA-256 and MD5 for every other packet file. Root review
and publication are separate steps; this worker has not uploaded or mailed
the packet.
