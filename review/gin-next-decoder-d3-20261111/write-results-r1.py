#!/usr/bin/env python3
"""Write D3 results and an English unsent draft from complete audited tables; no new statistics or filtering."""
import argparse
import hashlib
import json
import pathlib

HERE = pathlib.Path(__file__).resolve().parent


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=pathlib.Path, default=HERE)
    parser.add_argument('--output', type=pathlib.Path, required=True, help='Existing owned documentation directory')
    args = parser.parse_args()
    root = args.root
    audit = json.loads((root / 'INDEPENDENT-FULL-RECOUNT-r1.json').read_text())
    assert audit['status'] == 'PASS_INDEPENDENT_COMPLETE_RECOUNT'
    assert (audit['raw'], audit['retained'], audit['warm'], audit['numeric_comparisons']) == (3136, 2688, 448, 87360)
    primary = json.loads((root / 'tables-r1/PRIMARY.json').read_text())
    assert len(primary) == 56
    by_case = {(entry['cohort'], entry['case']): entry for entry in primary}

    def ratio(name, left='B', right='D3'):
        return ' / '.join(f"{next(pair['percent']['median'] for pair in by_case[c, name]['pairs'] if (pair['left'], pair['right']) == (left, right)):+.2f}%" for c in range(2))

    def absolute(name, role='D3'):
        return ' / '.join(f"{by_case[c, name]['absolute'][role]['median']:.4f}" for c in range(2))

    diagnostics = json.loads((root / 'tables-r1/CONTROLS-AND-NEGATIVES.json').read_text())
    controls = []
    for cohort in range(2):
        for kind, metric in [('decoder', 'decoder_allocation_materialization_free_cpu_ms'), ('sql', 'sql_execution_ms')]:
            entry = next(value for value in diagnostics if (value['cohort'], value['kind'], value['metric']) == (cohort, kind, metric))
            controls.append(f"| {cohort} | {kind} | {entry['twin_case_median_percent_min']:+.2f}% to {entry['twin_case_median_percent_max']:+.2f}% |")
    findings = f"""# D3: selective decoder gains with remaining tradeoffs

D3 reduces D2's multi-byte-delta overhead and retains its dense decoding gain in this fixed comparison, but it is not a general upgrade over D2. It loses the D2 benefit when a long delta appears first and dense deltas follow, and it gives back much of the first-singleton/growth benefit. Delta2, singleton and small-input regressions remain. Whole SQL results are mixed.

All percentages below are medians of direct per-round ratios, positive meaning slower. Slash-separated values are cohort 0 / cohort 1; they are not pooled. Absolute medians are milliseconds per complete native or SQL command. A ratio median need not equal the ratio of absolute medians. All 12 retained observations, min/max/mean/sample-stdev/MAD and all six role pairs are retained.

## Decoder outcome

- Dense128 D3/B is {ratio('decode_dense128')}, versus D2/B {ratio('decode_dense128', right='D2')}. Absolute B CPU is {absolute('decode_dense128', 'B')} ms and D3 is {absolute('decode_dense128')} ms for the complete 20,000-loop command.
- Delta3 moves from D2/B {ratio('decode_delta3', right='D2')} to D3/B {ratio('decode_delta3')}; delta4 moves from {ratio('decode_delta4', right='D2')} to {ratio('decode_delta4')}. These observations approach B in this grid, without establishing equality or a universal fix.
- Delta2 still costs {ratio('decode_delta2')} versus B, although D3/D2 is {ratio('decode_delta2', 'D2', 'D3')}. Delta5 and delta7 also retain small positive case medians in at least one cohort.
- Alternating one-/multi-byte deltas improve from D2/B {ratio('decode_alternating_one_multibyte', right='D2')} to D3/B {ratio('decode_alternating_one_multibyte')}. Dense-first/long-later D3/B is {ratio('decode_dense_first_then_long')}.
- The prospectively declared long-first/dense-later negative is concrete: D2/B is {ratio('decode_long_first_then_dense', right='D2')}, but D3/B is {ratio('decode_long_first_then_dense')}, so D3/D2 is {ratio('decode_long_first_then_dense', 'D2', 'D3')}. Selecting scalar for the whole segment gives back the late dense benefit in this case.
- First-singleton/growth D3/D2 is {ratio('decode_first_singleton_grow', 'D2', 'D3')}; D3/B is only {ratio('decode_first_singleton_grow')}, compared with D2/B {ratio('decode_first_singleton_grow', right='D2')}. Singleton-segment D3/B is {ratio('decode_singletons')}. Batch4, batch5 and batch8 also become slower than D2 in both cohorts; every value and range remains in the full tables.

The native inner CPU includes the actual backend decoder's allocation, TID materialization and free. Input generation, compression and full-output verification are outside that clock. Backend command CPU and client wall time are separate metrics in the JSON and all-metric tables. These are allocation-inclusive backend workloads, not isolated instruction fragments.

## Whole SQL outcome and controls

Skew1000 D3/B executor time is {ratio('skew1000')}: B {absolute('skew1000', 'B')} ms to D3 {absolute('skew1000')} ms for the entire 100-probe command. D2 is {absolute('skew1000', 'D2')} ms, with D2/B {ratio('skew1000', right='D2')}; D3/D2 is {ratio('skew1000', 'D2', 'D3')}. D3 therefore retains a modest B-relative benefit here while giving back some of D2's benefit.

Dense SQL D3/B is {ratio('dense_and')}; prefix is {ratio('prefix')}; rare is {ratio('single_rare')}. Forced OR is {ratio('or_forced')} and forced single-term is {ratio('single_forced')}. D2's forced OR/single regressions in cohort 0 ({ratio('or_forced', right='D2')} and {ratio('single_forced', right='D2')}) do not repeat in cohort 1, so the first-cohort reduction is not a stable universal-repair result. The ID-only Seq control is {ratio('seq_control')} and has no GIN predicate. SQL timings refer to the complete fixed repeated-probe EXPLAIN command, not a per-request latency estimate.

Exact B/T controls are retained without correction. The ranges below are the minimum and maximum case medians for each primary metric, not confidence intervals:

| Cohort | Primary metric family | T/B case-median range |
|---|---|---:|
""" + '\n'.join(controls) + """

All CPU, wall and executor controls and every positive D3/B or D3/D2 case median are listed in `tables-r1/CONTROLS-AND-NEGATIVES.json`. Sign alone is not a significance classification. There is no pooling, trimming, twin normalization or source-causal attribution.

## Evidence and limits

The accepted campaign contains 3136 raw commands: 2688 retained and 448 warm, 21 native decoder cells and seven SQL cells. Two fresh cohorts each use two warm and 12 retained balanced four-role rounds. The independent recount passed all 87,360 numeric comparisons, 672 absolute groups, 1008 pair groups and 12,096 direct round pairs. Both independent regenerations are byte-identical to the canonical analyses. Raw and literal journals remain plain JSONL.

The extra observation review checked 224 case/role setting objects against 12 explicit expected GUC values each, 784 actual SQL plans, 200 historical ordered Seq/index reference hashes, eight backend/source/ELF/header/module bindings and the final 17-lifetime shutdown proof. No production source, expected output, loop, threshold or case was changed after the freeze.

Four clean backend builds B/D2/D3/D3_assert each passed the original 239 core and posting tests. The finite ordinary gate passed 188 ordered/prepared SQL and 48 lifecycle comparisons, 84 decoder cases/54,144 item checks, and 768 valid boundary cases/1536 decode calls/33,408 item checks. The old fixed-B reference is unchanged. Assertion-build object equality is not applicable because its flags differ. Auxiliary auditor draft errors are preserved separately from actual runtime PASS.

Normal full-build ASM matches the reviewed r2 translation unit: no outlined decode_varbyte calls, a 24-byte local frame and the same six saved registers. D3 remains 1241 bytes versus D2 844 and B 589. The extra static growth-call site does not prove extra runtime allocations. D3r1's helper outlining and 56-byte local-frame outcome is retained as a codegen-only negative; it was not timed as a full backend.

The bounded host monitor recorded 49 five-second endpoint samples, load1 0.1538–1.1099, and covered the accepted campaign status interval. Recorded controller/runner/backend PIDs account for the major Python/PostgreSQL consumers. Other low activity remains visible. Endpoint/top20 snapshots can miss short-lived work; there is no per-thread affinity, host-steal or CPU-frequency proof. The two CPU placements are on one VM, not a second-host replication. Retained command read/write bytes and major faults were zero in both cohorts; this is not a disk-cold experiment.

The actual root final proof confirms 17 owned lifetimes stopped, controller PIDs gone and source, four installed prefixes, headers, modules, seeds and frozen inputs unchanged. This is a finite ordinary performance experiment, not arbitrary concurrency or general merge qualification. Fresh Linux replay remains a static-validated frontdoor until a new Linux run through it is actually performed. The completed recorded-data offline replay is a separate local validation.

## Complete primary table

""" + (root / 'tables-r1/PRIMARY.md').read_text() + """

All three metrics, absolute spread statistics and direct pairs are in `ALL-ABSOLUTE.md`, `ALL-PAIRS.md` and the unchanged `analysis0-r1/` and `analysis1-r1/` JSON. D2 and D3 are independent alternatives over the same fixed B; the comparison does not stack their standalone patches.
"""
    draft = f"""UNSENT — not sent to the mailing list
Subject: [PATCH experiment] Select a GIN posting-list decoder loop per segment

This experiment follows our D2 decoder prototype. D3 selects the existing four-item batch loop or the baseline scalar loop once at the start of each posting-list segment. The format, allocation-growth contract and batch width do not change. The first four encoded bytes select the batch-capable loop only when they are all single-byte deltas; otherwise the whole segment takes scalar decoding.

The measured result is selective. D3 reduces the delta3/4 and alternating-delta costs while retaining dense decoding gains, but it is not a general D2 upgrade. The fixed screen deliberately measures both mixed directions and keeps every previous negative/control.

Two fresh cohorts used B, an exact B twin T, D2 and D3: 28 cells, two warm and 12 retained balanced rounds, 3136 raw commands/2688 retained/448 warm. A separate 112-command smoke accepted no samples. All percentages below are paired per-round median changes, cohort 0 / cohort 1, positive meaning slower; no cohorts are pooled and the twin is not used as a correction.

Dense128 D3/B is {ratio('decode_dense128')} (B {absolute('decode_dense128', 'B')} ms; D3 {absolute('decode_dense128')} ms for the complete 20,000-loop command). Delta3 moves from D2/B {ratio('decode_delta3', right='D2')} to D3/B {ratio('decode_delta3')}; delta4 moves from {ratio('decode_delta4', right='D2')} to {ratio('decode_delta4')}. Alternating one-/multi-byte deltas move from D2/B {ratio('decode_alternating_one_multibyte', right='D2')} to D3/B {ratio('decode_alternating_one_multibyte')}.

The negatives remain important. Delta2 D3/B is still {ratio('decode_delta2')}, and singleton segments are {ratio('decode_singletons')}. Long-first/dense-later loses the D2 benefit: D3/D2 is {ratio('decode_long_first_then_dense', 'D2', 'D3')}, while D3/B is {ratio('decode_long_first_then_dense')}. First-singleton/growth is {ratio('decode_first_singleton_grow', 'D2', 'D3')} slower than D2. Batch4/5/8 also give back some D2 gains. All 28 cells and ranges accompany the packet, without filtering the small negatives.

Whole SQL is mixed. The complete 100-probe skew command changes from B {absolute('skew1000', 'B')} ms to D3 {absolute('skew1000')} ms, D3/B {ratio('skew1000')}; D2 remains faster at {absolute('skew1000', 'D2')} ms. Dense SQL is {ratio('dense_and')}, prefix {ratio('prefix')}, rare {ratio('single_rare')}, forced OR {ratio('or_forced')} and forced single-term {ratio('single_forced')}. D2's first-cohort OR/single regression does not recur in the second cohort, so this is not a universal SQL repair. The ID-only Seq control is {ratio('seq_control')} and has no GIN predicate. Exact-twin ranges and all backend CPU/client wall/executor metrics remain visible in the tables.

Native inner CPU includes actual backend allocation, TID materialization and free; input generation, compression and full-output checking are outside that clock. Whole backend CPU and client wall time are separate metrics. SQL EXPLAIN execution time covers the complete repeated-probe command. The packet includes absolute median/min/max/mean/sample-stdev/MAD and all six direct role pairs.

Four fresh B/D2/D3/D3_assert full backend builds passed the original 239 core and posting tests without changing expected output. The ordinary gate passed 188 ordered/prepared SQL and 48 lifecycle comparisons, 84 decoder cases/54,144 item checks and 768 valid mixed-boundary cases/33,408 item checks. Independent arithmetic recounted all 87,360 numeric fields. Final root proof records 17 stopped owned lifetimes and unchanged source, installed prefixes, modules, seeds and frozen inputs. These are finite ordinary checks, not a general concurrency or merge-readiness claim.

The initial source revision is retained as a codegen-only negative: GCC outlined decode_varbyte and enlarged its local frame to 56 bytes. It was not timed as a full backend. A focused second revision uses PostgreSQL's existing pg_always_inline macro. Actual full-build normal ASM has no helper calls and the same 24-byte local frame/six saved registers as B and D2, but its function is larger: 1241 bytes versus 844 for D2 and 589 for B. Code size remains a tradeoff; no latency cause is inferred from that observation.

Raw B72 is72b9498df9a369e747f8d96efb5a6cd33c2451e2; fixed B is8a8c475037bfde101da23cc9b0364c9c020eca93. D2 isa85a9242f455b12c93528f3ace33eb69b6cd1008. D3r2 is1ce29c18ceb41882deced3ebe680ee75ba2c29b0; r1da951d2777e7b021966e5c9ade770bd434242e15 is archived separately. D2 and D3 standalone patches are alternatives, not a series. The shared fixed prerequisite is identical in every tree.

This is a measured local decoder heuristic, not a claim of a new general decoding algorithm. The previous general GIN performance discussion is context, not a direct decoder match:
https://www.postgresql.org/message-id/52F373CC.4050800%40vmware.com

The source and replay packet contains exact diffs/format patches, full source/header/ELF bindings, actual normal ASM, plain raw/literal journals, all controls and negative results, and Linux build/setup/native/SQL instructions. The portable fresh-host frontdoor is static-validated only; actual historical runs used the recorded root controllers. Local recorded-data replay is distinct from a new Linux run. The bounded monitor covers the campaign but can miss short-lived/thread activity and does not measure frequency or steal time. No second-host or disk-cold claim is made.
"""
    # Keep identity prose readable without changing any revision bytes.
    draft = draft.replace('is72b', 'is 72b').replace('is8a8', 'is 8a8').replace('isa85', 'is a85').replace('is1ce', 'is 1ce').replace('r1da951', 'r1 da951')
    args.output.mkdir(parents=True, exist_ok=True)
    for name, content in [('RESULTS.md', findings), ('email-draft-unsent.txt', draft)]:
        (args.output / name).write_text(content)
    receipt = dict(status='PASS_ACTUAL_AUDITED_NUMBERS_RENDERED', audit_sha256=hashlib.sha256((root / 'INDEPENDENT-FULL-RECOUNT-r1.json').read_bytes()).hexdigest(),
                   primary_rows=56, all_28_cells_retained=True, manual_percent_rounding=False,
                   files={name: hashlib.sha256((args.output / name).read_bytes()).hexdigest() for name in ['RESULTS.md', 'email-draft-unsent.txt']})
    (args.output / 'RESULTS-RENDER.json').write_text(json.dumps(receipt, indent=2) + '\n')
    print(json.dumps(receipt))


if __name__ == '__main__':
    main()
