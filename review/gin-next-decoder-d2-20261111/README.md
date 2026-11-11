D2 GIN decoder: completed matched backend and SQL experiment

D2 reduces the D1 multibyte decoder penalty and retains dense gains, with remaining tiny/multibyte and SQL negatives. This is an experimental tradeoff, not a general upgrade recommendation. The measured primary results include delta2 D2/B +4.52/+5.12% (D1/B +37.86/+38.11%) and dense128 D2/B -10.71/-10.80%, across two fresh placements on one host. See [RESULTS.md](RESULTS.md) for every case and absolute range, and [the unsent English draft](email-draft-d2-UNSENT.txt) for the contribution and limitations.

Actual historical execution: four full clean builds and unchanged core239/posting tests; ordinary qualification across B/D1/D2/D2_assert; independent 100-command smoke with no accepted samples; one fixed 2,800-command campaign (2,400 retained / 400 warm). The independent recount matches 78,000 fields, 600 absolute groups, 900 pair groups and 10,800 direct pairs. The root final live proof records all 17 runtime lifetimes stopped and unchanged source, four prefixes, headers, modules, seeds and scripts. No fresh Linux execution is claimed for the new portable frontdoor.

Source identities and alternatives:

- Raw PostgreSQL B72: 72b9498df9a369e747f8d96efb5a6cd33c2451e2.
- Common fixed B: 8a8c475037bfde101da23cc9b0364c9c020eca93; identical prerequisite in all trees.
- D1: c2b5dd6f9012cc4a27628c9d6c507ac467795ac5.
- D2: a85a9242f455b12c93528f3ace33eb69b6cd1008, branch experiments/gin-next-decoder-byte4-firstbit-v2-20261110.
- D1 and D2 are independent alternatives over fixed B. source/ contains both standalone patches and the D1-to-D2 review diff. inputs/build-source/ contains exact raw-B72 overlays and source snapshots. Source-only historical receipts retain their original dated status; actual execution evidence is separate.

Packet layout:

- inputs/: exact frozen build, qualification and timing scripts/manifests; no baseline archive. The original preparation READMEs remain unchanged historical records.
- recorded/build-qualification-r1/: 329 root-collected text proofs and their SHA manifest, including source/header/object inventories, flags, ELF identity, normal full-TU ASM and ordinary SQL/native results. No binaries or database files.
- recorded/timing-r1/: smoke/cohort plans, settings, ordered digest comparisons, command receipts, freeze and stop metadata. Whole-line gzip raw/literal chunks live in raw-chunks/; restore-raw-r1.py reconstructs all 77 exact timing files.
- analysis0-r1/ and analysis1-r1/: all three metric boundaries, complete absolute statistics, all six pairs and every direct round pair. tables/ renders every absolute/pair group and all 25 primary cells, with observed negatives and exact-twin ranges. Cohorts are never pooled or normalized.
- reviews/: actual root gate, smoke approval, final live and independent recount receipts, plus clearly separated local-auditor reporting errata. D2_assert release-object comparison is null/not applicable; no identical-object claim is made for its different configuration.
- normal-asm-review-r1/: selected actual guard-order evidence with object/source/ELF hashes. This confirms code generation, not the cause of every timing difference.
- fresh-replay-r1/: static-tested portable build/ordinary-gate frontdoor and full fresh-Linux instructions. historical-launch/ holds the original namespace-specific import/launch/live helpers for provenance, not fresh replay.

Run [REPRODUCE.md](REPRODUCE.md) for byte-exact offline replay and fresh Linux commands. The offline packet wrapper was actually executed locally: all six analysis files were byte-identical, the ordinary independent gate recount matched except timestamps, and the full 78,000-field recount passed. That is recorded-data validation, not a second Linux build or benchmark.

This is an assembled review candidate. Root owns final review, freeze, Git/S3 publication and any later work. The English email remains UNSENT.

NEXT-DECODER-HYPOTHESIS-r1.md is a separate read-only research note. It records that D2 ASM already reuses byte0 and does not establish a new redundant first-byte test or a D3 result. No new implementation or benchmark is part of that note.
