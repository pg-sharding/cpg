# Independent combined-hash raw and mathematics review

This is a new, separate audit tool. It does not edit or import the frozen benchmark/build harness. It imports only Python standard-library modules; it never imports analyze.py, its metrics/spread functions, runner.py, common.py or schedule.py. Source can be read to understand the recorded format, but implementation and formulas are separate.

Preparation is **STATIC ONLY**. No collected campaign data has been supplied and no campaign result has been audited yet. The static command checks known small mathematical vectors and independently reconstructs the prospective design; it does not manufacture synthetic benchmark rows or performance results:

```sh
python3 -B audit-independent.py --help
python3 -B audit-independent.py --static-check
```

The Williams row is derived as0,+1,-1,+2,-2 modulo5, then five cyclic label shifts and their five reversals. Position and ordered adjacency counts are independently checked. Two warm rows precede all ten retained rows per case. The second cohort reverses case order; numeric role births reverse B/T/N/H/C to C/H/N/T/B. Exact chronological row fields are checked for all1140 observations per cohort.

After root collects the compact original receipts and raw data, use a new output directory:

```sh
python3 -B audit-independent.py \
  --collection /local/collected/run \
  --analysis /local/derived-analysis \
  --runtime /local/collected/runtime.json \
  --fixture /local/collected/fixture-receipt.json \
  --build-receipt /local/collected/build-receipt.json \
  --gate-status /local/collected/gates/status.json \
  --holdout /local/collected/holdout-discovery.json \
  --output /local/new-independent-review
```

`--collection` preserves the run layout: outer `status.json`, `CONTROLLER-FREEZE.json`, and `cohort0/` and `cohort1/` each with `status.json`, `FREEZE.json`, `backends.json` and exactly one of `raw.jsonl` or lossless `raw.jsonl.gz`. Compressed raw is decompressed in memory; both compressed and original byte digests are reported, and the original digest is compared with runner/analyzer receipts. No existing raw or output file is rewritten. `--harness` and `--source-plan` default to this packet's frozen sibling source paths and can point to their unchanged collected copies. Analysis must contain original `absolute.json`, `pairs.json`, `absolute.csv`, `all-ten-pairs.csv` and `status.json`.

Every2280 raw literal answer,19-case plan policy, source/harness-input digest and chronological design field is checked. The exact independently implemented full-node recorded signature includes loops, rows, rechecks, filters and Memoize counters and must match all roles/rounds and both cohorts plus saved state. Retained root plans must have zero shared reads. Actual hot-rescan3000 loops, natural Memoize1 loop/2999hits, residual3000loops/no Memoize hits, collision4999 rechecks and engineered chain work remain mandatory. A richer structural-field comparison is diagnostic only; it is not a new timing acceptance criterion.

The tool independently forms570 absolute groups and1140 direct pair groups. All ten unordered role pairs use the same retained round2..11. It compares all11400 individual left/right pairs, every raw value array, and minimum/median/maximum/mean/sample standard deviation/unscaled MAD in JSON and CSV. There are2850 distributions (absolute, pair difference, pair percentage) and17100 numeric distribution statistics before the duplicate CSV checks. Mean uses math.fsum; variance explicitly divides by n−1; median sorts values; MAD is the median absolute distance from that median. Pair percentage is100*(right−left)/left per round, not a quotient of medians. Numeric comparison tolerances are2e−12 relative and1e−10 absolute for floating-point evaluation differences.

Source→build→gate→runtime→freeze→backend digests are cross-bound. T must map to B's exact recorded source, prefix and ELF on a distinct postmaster; releases share flags. Local source patches/snapshots are hashed; source/header inventory digests are independently reconstructed from recorded manifests. Installed ELF/header/module/PGDATA files are not included in clean collections and are **not reread by this offline tool**. Their actual execution checks remain original recorded receipts. The tool verifies those bindings, counts and cleanup evidence, and labels that limit explicitly.

Success produces a new `INDEPENDENT-AUDIT.json` with status `PASS_INDEPENDENT_RAW_MATH_AND_RECORDED_BINDINGS`. A failed audit preserves its failure report. It does not approve a performance conclusion, fabricate Linux replay, normalize controls, discard cases, trim samples, pool cohorts or authorize another timing run. A checklist is in `RESULT-READINESS.md`.
