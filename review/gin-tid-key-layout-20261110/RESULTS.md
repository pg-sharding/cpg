# GIN preserved-layout follow-up: the absent regression remains

R2 is complete. P11 keeps the four-byte BlockId load and restores the original key shift. It retains substantial selective-query gains, but does not remove the repeated absent-query cost. It is not promoted to full SQL or CREATE INDEX. C11 is a source-only combined counterpart with production-unit/property preflight; no full C11 build or C11 timing is claimed.

## Exact experiment

Fixed B72 baseline B: `8a8c475037bfde101da23cc9b0364c9c020eca93`, raw B72 `72b9498df9a369e747f8d96efb5a6cd33c2451e2` (20devel), same supplied prerequisite in every source. P10: `ca701de010d76b469d9fbfa09f4cad2fdb996e64`; P11: `a5e258877d0fcebc417c020351919a7e2706a7fe`. This is not current master. P11 was actually cherry-picked from C11 `ca6ad39111cd67f20ff2dd3a8f619239d0360a10`, after authoring the source once on C10.

P10 and P11 differ by restoring `block <<32 | offset`. The same bounded four-byte memcpy, little-endian halfword reorder, six-byte storage and two-byte alignment remain. Every new P11 transient key matches the original baseline expression, not just its ordering. The complete P11 diff is a header-only change after fixed B.

## All main direct CPU comparisons

Each cell is cohort0 / cohort1: medians of12 direct same-round percentages. Negative means less CPU. SQL rows use whole-command backend CPU; AM rows use internal process CPU of the real scan loop. No cross-wave subtraction, pooling, trimming or twin normalization. Medians of paired percentages are not ratios of aggregate medians.

| Case | P10/B % | P11/B % | P11/P10 % | T/B % |
|---|---:|---:|---:|---:|
| skew1000 | -20.56 / -20.30 | -22.14 / -20.65 | -0.95 / +0.25 | -0.10 / -0.57 |
| skew127 | -7.37 / -13.84 | -14.42 / -12.88 | -5.84 / -0.24 | +0.51 / -0.47 |
| dense_and | -5.67 / -3.65 | -7.05 / -0.88 | -1.10 / -0.77 | +2.27 / +0.26 |
| or_forced | -2.21 / +1.84 | -1.87 / -0.38 | -1.21 / -1.70 | +0.94 / +2.22 |
| single_forced | -1.08 / -1.70 | -2.95 / -0.60 | -1.73 / +0.99 | -1.99 / -1.67 |
| single_rare | -1.67 / -1.91 | -0.25 / -1.58 | +0.39 / +0.62 | +1.29 / -0.40 |
| inline | +0.85 / -0.92 | +2.55 / +1.47 | +0.00 / +2.63 | +0.83 / +2.77 |
| jsonb | -20.95 / -23.01 | -18.69 / -22.91 | -0.32 / -0.03 | +0.95 / -0.04 |
| lossy_and | -2.35 / -3.03 | -1.86 / -2.05 | +0.96 / +0.73 | +0.18 / +0.90 |
| seq_control | +2.99 / +3.04 | +0.63 / -1.88 | -3.46 / -2.04 | +1.89 / +2.17 |
| skew_group4096 | -22.29 / -21.81 | -22.60 / -19.54 | -0.01 / +0.49 | +0.11 / +0.70 |
| inline_single | -1.77 / -3.75 | -2.64 / -2.58 | -0.77 / -1.46 | +0.30 / +1.41 |
| absent | +5.64 / +5.19 | +4.04 / +4.17 | -0.67 / -1.97 | +2.70 / +0.78 |
| am_inline | -7.76 / -8.70 | -8.09 / -6.87 | +0.06 / +1.48 | -0.28 / +0.97 |
| am_absent | +4.82 / +4.60 | +5.79 / +5.95 | +1.36 / +1.27 | +0.97 / -0.14 |
| am_skew1000 | -23.36 / -23.63 | -23.08 / -23.05 | +0.37 / +0.22 | +0.07 / +0.22 |
| am_full | -9.34 / -7.60 | -7.58 / -1.65 | -0.95 / +0.90 | -0.92 / +1.62 |
| am_or | -6.50 / -7.57 | -6.72 / -6.10 | -0.36 / +1.34 | +0.86 / -0.44 |
| am_dense | -9.62 / -9.61 | -10.08 / -8.67 | -0.21 / +1.15 | +0.38 / -0.51 |
| am_rare | -8.68 / -5.56 | -7.01 / -7.33 | +1.88 / +0.77 | +1.81 / -0.46 |

## Absolute CPU and spread

Every cell is min / median / max ms across12 retained observations. All executor/client-wall metrics, absolute groups, SD/MAD, direct per-round values and all negatives are in results/*/tables/ALL-RESULTS.md, CSV, JSON and raw evidence. AM values are per complete loop, not per SQL query or scan.

| Case | Cohort | B ms | P10 ms | P11 ms |
|---|---:|---:|---:|---:|
| skew1000 | 0 | 78.117942 / 78.752187 / 122.283486 | 60.991760 / 63.087739 / 79.296702 | 60.805418 / 61.431648 / 68.621208 |
| skew1000 | 1 | 77.629039 / 79.087297 / 121.239971 | 60.963456 / 70.266008 / 104.451033 | 61.060732 / 62.404414 / 104.801180 |
| skew127 | 0 | 143.863845 / 148.087129 / 164.618466 | 127.792856 / 136.890354 / 200.346958 | 124.149889 / 128.911796 / 202.078716 |
| skew127 | 1 | 140.966747 / 147.960679 / 219.963508 | 122.619942 / 127.899130 / 201.976904 | 122.264258 / 126.692870 / 200.710685 |
| jsonb | 0 | 153.299568 / 154.424941 / 240.753420 | 120.665279 / 124.070475 / 209.082068 | 119.932037 / 125.175023 / 208.894115 |
| jsonb | 1 | 149.553064 / 151.647492 / 206.803758 | 114.973336 / 116.711189 / 134.919732 | 115.878414 / 116.604319 / 124.215587 |
| skew_group4096 | 0 | 58.950795 / 59.376078 / 71.064186 | 45.315862 / 46.184886 / 49.940091 | 45.611085 / 45.900048 / 51.695636 |
| skew_group4096 | 1 | 57.268881 / 59.606695 / 89.996009 | 43.719476 / 48.569049 / 77.411452 | 44.028249 / 47.335813 / 77.466634 |
| or_forced | 0 | 152.220277 / 158.629728 / 177.812838 | 151.108878 / 156.422003 / 157.998568 | 149.200035 / 154.947574 / 174.621978 |
| or_forced | 1 | 145.753691 / 153.013487 / 166.284415 | 146.175024 / 156.064242 / 173.282768 | 144.207181 / 155.732398 / 189.394410 |
| inline | 0 | 0.613230 / 0.638157 / 1.114012 | 0.615834 / 0.644928 / 0.907602 | 0.592128 / 0.641579 / 0.886621 |
| inline | 1 | 0.591217 / 0.617036 / 0.636605 | 0.578488 / 0.612760 / 0.658318 | 0.603636 / 0.626040 / 0.687963 |
| single_rare | 0 | 6.143030 / 6.302208 / 6.798483 | 6.100106 / 6.267646 / 6.688118 | 6.155959 / 6.249284 / 7.096481 |
| single_rare | 1 | 6.194006 / 6.293411 / 6.388468 | 6.008188 / 6.223796 / 7.704734 | 6.098012 / 6.241437 / 7.860407 |
| absent | 0 | 1.493701 / 1.525174 / 1.640061 | 1.571288 / 1.612084 / 1.983837 | 1.562675 / 1.594207 / 1.705910 |
| absent | 1 | 1.354783 / 1.403482 / 1.626060 | 1.425289 / 1.471483 / 1.578539 | 1.413682 / 1.456145 / 1.498259 |
| seq_control | 0 | 50.612852 / 63.147268 / 79.570531 | 52.441866 / 64.359512 / 85.272570 | 53.733845 / 59.783735 / 82.160299 |
| seq_control | 1 | 44.118735 / 61.633867 / 70.329202 | 54.230371 / 61.997073 / 76.626133 | 56.881960 / 62.524939 / 66.485193 |
| am_absent | 0 | 55.383622 / 56.159826 / 75.464800 | 57.935471 / 58.597550 / 78.764843 | 58.696063 / 58.981171 / 65.234336 |
| am_absent | 1 | 54.647517 / 55.615619 / 60.623576 | 57.603753 / 58.595923 / 62.264739 | 57.784315 / 58.677464 / 67.445294 |
| am_skew1000 | 0 | 72.369194 / 73.290166 / 76.795077 | 55.276891 / 55.940192 / 62.855425 | 55.554869 / 56.056852 / 92.738024 |
| am_skew1000 | 1 | 71.155723 / 71.886310 / 89.690891 | 54.671162 / 55.096626 / 66.100845 | 54.944152 / 55.308083 / 60.359860 |

## What this establishes

P11/B selective SQL CPU improves by -22.14 / -20.65% for skew1000, -18.69 / -22.91% for JSONB and -22.60 / -19.54% for group4096. The actual-AM skew loop improves -23.08 / -23.05%. These are direct observations in this new matched campaign, not sums of R1 or C9 gains.

The repair hypothesis fails: SQL absent remains +4.04 / +4.17%, actual-AM absent +5.79 / +5.95%. The old P10 regression reference also repeats in this campaign: SQL +5.64 / +5.19%, AM +4.82 / +4.60%. P11/P10 AM absent is +1.36 / +1.27%, rather than a repair. Both the new and prior negatives are preserved.

P11 SQL inline is +2.55 / +1.47% while native inline is -8.09 / -6.87%; the different boundaries must not be mixed. P11 Seq is +0.63 / -1.88%. P10 Seq is +2.99 / +3.04%; T/B Seq +1.89 / +2.17%. The latter off-path movements and exact-twin variation prevent a causal source-level explanation from being inferred. Every control stays in the tables.

Matched release P10/P11 have identical addresses/sizes for all26,849 defined ELF symbols. Their6,239,874-byte .text sections differ in exactly54 bytes, verified as x86-64 SHL immediate16->32; all other .text bytes match. This excludes changed function placement between these two linked ELFs. It does not establish an actual runtime instruction-trace identity, ASLR equivalence or the cause of measured differences. See evidence/ELF-SYMBOL-LAYOUT.json, evidence/ELF-TEXT-DIFFERENCES.json and ELF-INSTRUCTION-CHECK.json.

Separate actual-AM absent software profiles assign76.26% /77.44% /80.70% of sampled self time to ginPostingListDecodeAllSegments in B/P10/P11. These are normalized software samples, not a decomposition of the5–6% cost or a proof that this function regressed. The same broad decoding work dominates all three. More work is needed before recommending the load change generally.

No full25-query timing or CREATE INDEX measurement was executed. The source prototype is preserved, rather than presented as an accepted fix. The narrower old-layout variant avoids an unnecessary transient-layout change, but is not demonstrated to remove the runtime regression.

## Verification and repetition

Four new clean builds B/P10/P11/P11_assert at identical common source/build/compiled-prefix paths, separate installs, GCC13.3 -O2 -g -fno-lto, OpenSSL/no ICU/readline, nice10/make-j2. Every build passed original239 core tests and test_ginpostinglist. Original expected/source/header/install identities remain checked; every non-GIN backend object is byte-identical to B. Exact source, diff reapplication and code publication receipts accompany the packet.

Production P11/C11 units compile with release/assert headers. Both release helpers pass1,009,216 extreme/random/alignment cases, checking exact original keys and comparison results. Only x86-64 little-endian execution is claimed. C11 has no full-build/timing claim.

All four ordinary qualification variants passed100 ordered Seq/GIN row-multiset, scalar and path checks,32 prepared comparisons/cached rescans and28 native answer checks. Every timed role/cohort repeats all25 row multisets. All12 separate profiles succeeded. Screen:2,240raw/1,920retained/320warm, four roles B/T/P10/P11 with exact B/T twins,13 SQL plus seven actual-AM cases, two warm and12 retained Williams4 rounds, two reversed CPU/slot/session/case-order cohorts. All retained read/write/temp/WAL counters are zero.

Final checks verify13 stopped owned clusters,8 measured backends absent, no own processes/sockets and unchanged source/installs/seeds/runtime/modules. The local reconstruction verifies all536 absolute groups and804 pair groups against raw data, permitting only3e-15 relative tolerance for cross-Python sample-SD rounding. See REPRODUCE.md for dependencies, exact revisions/flags/data and native/SQL commands. The optional manual-analysis parent-directory preparation also clarifies the corresponding R1 instructions. Portable commands are supplied with the actual executed harness; no extra clean-machine replay is claimed.

## Attribution and artifacts

Integer TID comparisons and deferred decoding of copied compressed posting segments were already proposed by Heikki in [2014](https://www.postgresql.org/message-id/52F373CC.4050800%40vmware.com), a direct conceptual predecessor to C9. The present contribution is a small load/code-generation experiment with reproducible positive and negative measurements, not a new algorithm. The old uint64/32-bit compiler discussion in [2015](https://www.postgresql.org/message-id/20150719195033.GB1300191%40tornado.leadboat.com) provides portability context; it was not reproduced and establishes no current compiler status.

The immutable R1 packet is at https://github.com/pg-sharding/cpg/tree/experiments/gin-logical-tid-key-results-b72-20261110/review/gin-tid-key-20261110 . Its observations remain historical and separate.

`patches/P11-over-parent-candidate.diff` is the complete P11 diff after fixed B. The C11 equivalent applies after C9. Incremental diffs/format-patches apply after P10/C10 instead. Alternative branches/forms must not be applied twice. The UNSENT English draft, all raw observations, full distributions, code/source manifests and instructions are included. Public packets exclude PGDATA,executables,perf.data,full logs and private message bodies.

