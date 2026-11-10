# K3 finite installed-dispatch and ordinary SQL gate

This separate overlay adds no production change. It requires the exact four
fresh B/K1/K3/K3_assert builds from BUILD-INPUTS-K3-r1.json and the frozen
source plan 36e9b65f… . The controller waits for the one approved PID 447721,
with a 3600-second deadline and failed-build/early-exit refusal, then runs the
gate once. It never retries or launches timing. Build cleanup must finish and
the original PID must be absent before qualification begins.

The original exhaustive native oracle, vector probe, probe SQL, session and
all 25 ordinary SQL inputs/answers remain byte-identical to executed K1. Each
of four variants repeats 40 ordered Seq/GIN SQL multisets/scalars, 7 prepared
cases with repeated results, 12 one-session INSERT/DELETE/VACUUM lifecycle
comparisons, 11 exhaustive installed-dispatch native cases and 11 generic
VOLATILE support-wrapper fallback cases. Plans, scalar results, row digests
and native outputs are durably saved before Python acceptance checks. No
expected output is regenerated from K3.

The distinct sibling-reviewed budget helper compiles against each variant's
actual 907 installed private headers. EXPECT_TRI_CACHE is 0 for B and 1 for
K1/K3/assert; EXPECT_CONSECUTIVE_BUDGET is 0 for B/K1 and 64 for K3/assert.
It initializes real scan keys with actual support metadata and calls the
installed dispatcher, independently checking every result against the native
builtin and preserving both recheck sentinels. Private memo memory is opaque.
It checks 63/64/65 consecutive misses, a hit after 63 followed by a fresh full
budget, 96 cumulative misses separated by hits, permanent direct dispatch,
independent live keys, fresh context/key initialization and hidden/nine bounds.

There are 11 extra invocations per variant: 44 total, 51744 checked dispatches,
180 expected pointer transitions,528 initializations and88 context resets.
The independent single-term return literals are FALSE 394 / TRUE 400 / MAYBE 382
per invocation. Other return-count vectors must match across all four builds,
while every individual return is independently checked inside the helper.
This helper uses three uniform vector states; the unchanged exhaustive native
oracle supplies mixed-vector coverage. Context reset/reinitialize is not
labelled index_rescan; real prepared/ordinary SQL and the later actual-AM
rescan oracle supply their own separate evidence. The threshold counts key
dispatch calls, including startup checks, rather than output TIDs.

A new 128 MB-shared-buffer seed is created once, fully inventoried and stopped.
Four fresh private copies are hashed/fsynced and run sequentially. The gate
stops all five owned cluster lifetimes and clients in finally, checks no
pidfile/socket/PID remains, checks every installed tree, final full source,
build-helper and qualification input bytes, and verifies the seed unchanged.
All objects/modules, SQL rows and counters are synthetic and local to the
new /home/reshke/allfuzz/gin-cache-k3-20261110 namespace, ports 46200..46204.
No other cluster or older prefix is changed. Full runner logs remain local;
only selected bounded proof files will be collected.

This overlay has passed only local AST/help, exact source identity and an
independent finite-protocol recount. K3 qualification has not run. Only a
later actual PASS can authorize the separate zero-retained timing smoke.
No dense-regression repair, concurrency safety or merge readiness is claimed.
