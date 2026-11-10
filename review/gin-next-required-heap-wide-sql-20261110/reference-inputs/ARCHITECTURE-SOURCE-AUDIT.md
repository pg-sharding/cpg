# Heap wide-OR SQL follow-up: prelaunch architecture/source audit

Status: local source, AST/help and protocol review only. No VM operation,
new compilation, correctness execution or performance observation is claimed.

The published earlier Heap campaign had seven actual-AM dense unions at widths
1/2/7/8/32/128/512, but its ordinary SQL cells covered sharing/lossy/absent/Seq
controls rather than those same wide unions. New SQL measurements are needed;
AM inner times cannot be presented as SQL executor or end-to-end improvement.
The old results, including all negatives, stay immutable and separately scoped.

`cases.json` copies each exact old stored `query` expression from
`or-consistent/or/timing-r1/harness/inputs/timing-cases.json`, whose file hash
is bound in ORIGIN.json. The new SELECT changes only the old AM invocation
into `SELECT count(*),sum(id) FROM g1.docs WHERE d @@ '<same query>'::tsquery`.
N1 is common, N2 adds group0, then widths 7/8/32/128/512 end with group5/6/30/
126/510. N1/2/7 remain mandatory negatives. This is a SQL translation, not a
source port or a newly selected expression after seeing SQL outcomes.

The held source is exact historical fixed B72: raw B72
72b9498df9a369e747f8d96efb5a6cd33c2451e2, fixed B
8a8c475037bfde101da23cc9b0364c9c020eca93 and independent Heap
03dff8bfa5075e5838c7fbffc712d0b79d03f13d. The already published Heap source
creates its lower-bound required-entry heap only for nrequired>=8 with fuzzy
search disabled. It leaves tiny cases and fuzzy reduction on the original
path, repairs stale roots rather than ordering by mutable entry pointers,
and stores its heap in keyCtx. No such code, thresholds, state/frequency,
lossy/recheck semantics or callback dispatch is changed here. There is no
C9/K1/K3/startup/decoder combination. Prior Heikki2014 heap discussion and the
published old qualification remain provenance, not a new novelty claim.

The runner requires exact historical build receipt SHA 9569933f83177971adbded4fd448a9f0c809a8c03f7945252ea8f48e52f80388
and qualification SHA 5abb4e1c6111e29ab166148748d94915fcfe036f9b112f4e8fa61ff5614aa3c3.
It verifies all installed files and ELF/source identities, full 7726 source
inventory, stopped qualified seed and exact seed tree. B/T use the same prefix,
ELF and SQL entrypoint. No old PGDATA is started or modified: only new numeric
copies of the immutable seed are started. No helper/library is compiled.

The seed contains 200002 docs including two special rows. The seven positive
OR predicates return exactly ordinary IDs 1..200000. The new unchanged-code
Seq control explicitly selects id BETWEEN1AND200000 with every index path
disabled. All eight scalar answers are independently fixed to
200000|20000100000, where sum=200000*200001/2. The independent ordered oracle
constructs the literal sequence 1..200000 locally, not from a candidate result:
1288894 bytes and SHA01b59173dc3205893607560d9f6caca711aa6c0f3303db7bbccb99552a9fc33a.
Every role must match that ordered Seq digest and, for seven wide cells, the
ordered forced-GIN digest. Both unmeasured oracle plans are retained and their
Seq/GIN paths asserted. Seq control is deliberately Seq in both oracle paths.
All measured EXPLAIN JSON/literals and exact one-loop/index shapes are retained.

Three smoke copies and six accepted copies are all hashed and fsynced before
role assignment. Smoke starts only those first three, executes all eight cells,
stops all owned clients/clusters and verifies six accepted copies remain equal
to seed. Root must independently review the 24 raw smoke observations/zero
accepted samples, gates/plans/answers/bindings/copies/shutdown before a separate
fixed screen. Each measured cohort also repeats its untimed ordered gate first.
The screen is 384 raw/288 retained/96 warm, all six role permutations, all three
pairs and three separate metrics. Cohort 1 reverses cases and physical births.
No trimming, pooling, control normalization, significance or causal claim is
permitted. Read/write/runqueue and every other proc delta remain in raw data.

The same previously executed session metric code is reused byte-identically:
client wall ends on command reply, full backend CPU uses schedstat snapshots,
EXPLAIN Execution Time remains PostgreSQL's executor metric. Literal execution
before every EXPLAIN is an explicit extra warm execution. Parsing/journaling
is outside the measured command. The raw observation is durably flushed before
validation. Outer cleanup visits every owned cluster independently; clients
also have independent bounded cleanup. Failures are preserved without retry.

A mandatory previous-K3 run path must show PASS_FIXED_SCREEN, zero remaining
owned clusters, empty cleanup errors, stopped controls and absent PIDs before
any prepare/smoke/run stage proceeds. Root additionally owns the fresh VM158
lease and source/receipt review; these local scripts confer no timing lease.
The old actual build/seed hard bindings make this an exact reference campaign,
not a claimed independently tested portable fresh-build frontdoor. A later
publication can include the existing old source/build/fixture replay alongside
this SQL-only adapter without relabeling any old evidence.
