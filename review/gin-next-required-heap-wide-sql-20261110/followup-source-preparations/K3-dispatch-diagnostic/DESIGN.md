# Untimed K3 dispatcher diagnostic (source only)

Status: local source preparation only. No compiler, backend, SQL, new fixture,
or timing run has executed this diagnostic. It is separate from the completed
2576/2208/368 K3 comparison. All measured source and executables remain intact.

The question is whether the fixed 64-consecutive-miss policy actually switches
for dense, rare, full and OR work. The measured dense improvement does not
answer that question; the rare and prefix negatives also do not establish a
cause. Counts can distinguish an observed policy transition from a path that
never reaches the threshold. They cannot isolate machine-code/layout costs.

## Actual path and attribution

The parent is exact K3 `ec32d586cf3bb6cfa76eb672db70160b436ce47c`, whose
`ginlogic.c` SHA256 is
`9537f66e95ad8d9f45f12f4cc95d96339a29d21e724ef9c86737e2637fde9ec1`.
The diagnostic adds six observation calls and one local include to that TU.
Removing those insertions recovers the exact parent bytes. No callback
arguments, return expressions, cache conditions, miss increment, reset,
threshold, dispatch assignment or OID/address guard is replaced.

An opclass callback wrapper would fail K3's native-address/OID specialization
guard, so this probe does not use one. A separate backend records observations
inside the existing cached dispatcher and direct native helper. The unchanged
`FunctionCall7Coll` expression still invokes the actual builtin. All source
snapshots and the diagnostic overlay are separate files in this directory.

## Bounded observations

Backend-local fixed storage holds at most 128 initialized scan-key generations
per capture. A new initialization gets a new generation even when its pointer
address is reused after key-context reset. Lookup checks newest first. Reports
only read copied counters/vectors; they never dereference a retired key or
export its address. Any overflow rejects a capture; no partial-count conclusion
is allowed. The probe is disabled except inside the explicit capture window.

For each key that actually received K3's builtin cache, record:

- Actual cached dispatches, memo hits/misses, hit resets, native callback calls
  from the cache, native direct dispatches after a switch, and switch location.
- Actual consecutive-miss runs, with an exact 0..64 histogram, maximum and
  independent counter agreement. The source's actual counter controls policy;
  the diagnostic counter merely checks agreement.
- The ordered `entryRes` stream at every cached dispatch and every direct
  dispatch after disable, counted once per dispatcher call. Record equal-vector
  run lengths (1,2,3,4,5..8,9..16,17..32,33..63,64,65..127,128..255,256+), maximum
  run, changes and a non-cryptographic ordered checksum.
- Equal adjacent vectors observed after disable, explicitly labelled as
  potential repeat opportunities, not actual memo hits or proven saved work.
- Over-eight-entry and observer-contract counters. Planned queries have one or
  two entries; an unexpected overbound event is preserved and reviewed.

No per-event allocation, unbounded trace, clock, profiler, shared-memory state,
counter-driven query decision or logging syscall occurs in the observed path.
The observer has substantial overhead and changes code layout. Its times must
never be compared with the published K3 times.

## Finite scope: 18 reports

`CASES.json` pins the same fixture queries and existing literal answers.
There are no new selected data distributions or policy thresholds.

1. Six actual SQL statements: the original dense, rare-single, full-forced,
   OR-forced, unchanged Seq control and original prefix negative. Start capture, execute the exact old
   statement once, finish capture. The original outer scan counts remain
   10/100/5/5/5/100. Seq should initialize no GIN key. Each statement gets a separate
   report and the 128-key budget restarts for that statement.
2. Six actual-AM queries: dense, rare, full, OR, inline and absent, each with
   one and three real `index_rescan`/`index_getbitmap` iterations. That gives
   twelve reports and independently checks new key generations across rescans.

The actual-AM helper uses the active snapshot and real index AM, allocates and
frees one bitmap per iteration, and calls no extracted/modelled GIN loop.
Loops are hard bounded to 1..3. Scalar answers/AM tuple totals and ordered
Seq/GIN results are checked independently before interpreting counters.
Capture results must be written and fsynced before any literal/count assertion.
Failed observations, including unexpected key counts or overflow, remain saved.

Required count identities include dispatches=cached+direct,
native_calls=native_from_cache+direct, hits+native_calls=dispatches for these
bounded native paths, and weighted miss-run histogram total=misses. At most
one switch is allowed per key, at actual miss64. After it, cached dispatches
must stop. All three AM rescan generations should have equal stream/counter
summaries for the same immutable snapshot; generation IDs themselves differ.
Do not prescribe in advance that a particular target must switch.

## Future build/launch prerequisites (NOT RUN)

Use a new namespace, proposed
`/home/reshke/allfuzz/gin-cache-k3-dispatch-probe-20261110`, new source/build/
prefix/PGDATA/socket paths and a root-granted lease. Never relink or install
into the measured K3 tree. Root must review the overlay and full driver before
any remote transfer or build. No importer or runtime approval is supplied here.

A prospective build would apply exact K3 and then `diagnostic-over-exact-K3.diff`
to a fresh authentic B72 tree, retaining the same flags and installed headers.
Compile the complete production TU/backend normally; inspect actual call sites
and exported `gin_k3_diag_*` symbols, then compile `gin-dispatch-diag.c` against
that exact new prefix. No Fortify, stack-protector or source-policy change.
Recheck unchanged core/ordinary SQL answers on this new diagnostic backend
before interpreting its reports. Its provenance must say instrumented and
untimed. Previously measured executable hashes cannot be reused as its identity.

Use a fresh copy of the qualified seed, with full source/prefix/seed bindings.
The test module exports:

```sql
CREATE FUNCTION public.gin_dispatch_diag_begin() RETURNS void
AS '/new/owned/gin-dispatch-diag.so','gin_dispatch_diag_begin' LANGUAGE C;
CREATE FUNCTION public.gin_dispatch_diag_finish() RETURNS text
AS '/new/owned/gin-dispatch-diag.so','gin_dispatch_diag_finish' LANGUAGE C;
CREATE FUNCTION public.gin_dispatch_diag(regclass,tsquery,integer) RETURNS jsonb
AS '/new/owned/gin-dispatch-diag.so','gin_dispatch_diag' LANGUAGE C STRICT;
```

For actual SQL, begin/finish run in the same persistent backend as the exact
target statement. For actual AM, one module invocation brackets the real scan.
On a module error, PG_CATCH disables tracing; on client failure the owned
backend/cluster is closed by the future controller's finally cleanup. A run
still requires source/header/ELF checks, durable raw observations, statement
timeouts and final owned-PID/socket/shutdown proof. Those launch mechanics are
not claimed by a source-only helper.

No K4 source or new policy is implemented. First establish the actual paths;
any later policy would be a separate source hypothesis and separately frozen
comparison, retaining full/OR reuse and dense/rare/short-scan negatives.
