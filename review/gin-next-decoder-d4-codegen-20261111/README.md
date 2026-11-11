# D4 decoder draft and normal codegen only

As of 2026-11-11, D4 is canonical exploratory source commit `d2866655e3b0932ce449fe8ecbf3db52404fe4f8` over D3r2 `1ce29c18ceb41882deced3ebe680ee75ba2c29b0`. The sole changed file is `ginpostinglist.c`. Root completed four isolated normal full-TU compiles, and independent offline review passed. There is no D4 full backend build, valid-input qualification, AM/SQL run or timing result.

D4 lets a scalar-decoded segment return to four-item batching at a later short value. Its caller consumes the first byte and routes multibyte values to an inline continuation helper. This intentionally returns to a D2-shaped per-item choice and may retain D2's alternating-data cost. No format or allocation-policy change is intended. The observed release decoder is 838 bytes versus D2 844 and D3r2 1241, with the same 24-byte local frame and six saved registers. These are codegen observations, without a speed or instruction-saving claim. D2 already reused its first-byte load/test.

`DESIGN.md` explains the motivation, selected historical D3 outcomes, bounds/capacity reasoning, risks and the pending fixed qualification/micro/SQL plan. `NORMAL-ASM-REVIEW.md` gives the actual address-level codegen review. `COMPILE-ONLY.md` gives exact recorded command data, replay prerequisites and a new-directory-only staging command. The existing root helper is reused; no new performance harness is included.

The reviewable packet layout is:

- `source/`: canonical format-patch, cumulative diff, original draft diff and D4 source snapshot. The format-patch applies over D3r2. The cumulative diff applies over fixed B `8a8c475037bfde101da23cc9b0364c9c020eca93`; it is an alternative to the D3r2-plus-D4 route, not another patch to apply afterwards.
- `root-codegen-r1/`: exact four full-TU source inputs, bound 907-header manifest, argv, input metadata and the actual finite root compile helper.
- `evidence-codegen-r1/`: text outputs, per-command receipts and final actual status. It contains no objects or executables.
- `prior-control-codegen-r2/`: previous B/D2/D3 disassembly/nm text needed for the independent exact-control comparison.
- Root documents/receipts: design, codegen review, source/patch/push provenance, initial-stage source metadata, English UNSENT draft and offline review script/result.

From the packet root, replay the offline review to a new output outside the packet:

```sh
python3 -B review-codegen-r1.py --root . --prior prior-control-codegen-r2 --output /new/owned/peer-codegen-review.json
```

That command checks text/source/receipt hashes and codegen controls; it invokes no compiler or backend. Compile-only reproduction is separate and requires the already-installed matching toolchain and B prefix described in `COMPILE-ONLY.md`. The packet does not distribute headers, backend binaries or system toolchains. Whole-object hashes are execution receipts and cannot be recomputed from text alone. The original inherited environment/system-header closure was not fully captured.

`SOURCE.json` is immutable historical metadata from the initial source-only stage. Later `SOURCE-COMMIT-r1.json`, `SOURCE-PUSH-r1.json` and actual codegen receipts supersede its stage interpretation; they do not rewrite it. `OBSERVED-D3-RESULTS.json` is selected context from the earlier D3 screen and is never D4 performance evidence. The complete earlier D3 performance packet is separate.

Root reran the packaged offline review and obtained the byte-identical peer receipt. ROOT-PACKET-REVIEW-r1.json records the final review; MANIFEST.json binds the frozen packet. Git/S3 delivery receipts are kept separately. Future full backend qualification and timings remain pending. No messages have been sent; `email-draft-UNSENT.txt` is a draft only.
