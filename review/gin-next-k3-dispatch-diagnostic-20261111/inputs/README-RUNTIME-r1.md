# Finite untimed dispatcher qualification and capture

This is a separate instrumented K3 experiment on VM84. Its source parent is
exact K3 ec32d586cf3bb6cfa76eb672db70160b436ce47c; the measured K3 source,
installed prefixes, PostgreSQL data and fixed timing results remain unchanged.
The observer snapshot later received canonical commit b267e8808ad9d9c3574eb89d047761704266a757.
Historical SOURCE/build inputs retain instrumented_commit:null; the later Git
mapping does not change their content or reproduce any earlier executable.

run.py waits at most 3600 seconds for the exact own build PID and successful
final build status. A failed/early-exit build stops the chain. Each stage may
run only once into a nonexistent output directory; every failure is retained.
The pipeline contains no latency sampling or accepted benchmark run.

The qualification uses unchanged native-oracle.c, budget-oracle.c, vector-probe.c,
Session, setup.sql and the 25 original SQL/answer inputs. The single DIAG role
keeps 40 ordered SQL cases, 7 prepared cases, 12 ordinary INSERT/DELETE/VACUUM
lifecycle comparisons, 11 mixed-vector native cases, 11 consecutive-budget
boundary cases and 11 generic VOLATILE callback fallback cases. It compares
ordered digests, native return counts and generic fallback observations with
byte-bound prior fixed-B evidence and independent Seq results. No expected
result is collected from the new instrumented candidate and substituted.
The observer remains disabled throughout this qualification.

Only after that gate PASS and both gate clusters are stopped does capture.py
compile the diagnostic module against the actual 907 installed headers/flags.
It creates a fresh byte-verified, fsynced copy of the newly qualified seed.
One additional owned cluster performs exactly 18 reports: 6 original SQL
statements (dense,rare,full,OR,Seq,prefix) plus 6 actual-AM queries with 1 and 3 real
index_rescan/getbitmap iterations each. There is no clock/CPU metric in a report.
Session.measured is never called. The shared-load environment is counts-only.

SQL/scalar answers, ordered Seq/index digests and actual-AM tuple totals are
independent checks. Literal and full observer JSON are saved/fsynced before
capture acceptance assertions. Counts check dispatch/native/hit/miss identities,
exact weighted miss histograms, bounded vector-run histograms, miss64 switches,
absence of cached dispatch after disable and new generations across rescans.
No workload is required in advance to switch: the observed policy path is the
question. Overflow, counter errors, an unexpected generation or tuple count
fail the preserved attempt. Raw data remains available before that failure.
The observer records actual vectors after disable; equal adjacent values there
are labelled potential repeat opportunities, not actual memo hits.

All subprocesses inherit a 3 GB address-space cap and nice 10. Root's j1 backend
build is separate. Qualification and capture use short sockets under the owned
namespace/s directory:81/82 encoded socket-path bytes, below 104. Ports are
46700(seed),46701(qualification),46710(capture); core/posting use 46640/46670.
No unrelated PID is signalled. Before any pg_ctl-stop the actual PID/ownUID/ELF
and datadir are checked, and finally attempts all owned stops. Source, install,
seed and frozen helper bindings are checked again after successful execution.

After independent source review, root may queue the finite stages:

```sh
R=/home/reshke/allfuzz/gin-cache-k3-dispatch-probe-20261110
python3 -B "$R/inputs/run.py" --root "$R" --stage qualify-and-capture \
 --wait-build-pid 4162785 --wait-seconds 3600
```

For staged review, use --stage qualify and, only later, --stage capture.
Capture accepts only the successful qualification receipt from this build;
it never reuses the measured K3 executable. Actual normal full-TU ASM and
nm-D exported-symbol evidence must accompany the final report.

Local RUNTIME-STATIC-r1.json proves Python AST/help, unchanged oracle bytes,
finite expected counts and short socket paths only. The runtime module,
qualification and 18 reports have not executed during this local preparation.
No new production policy, threshold, performance repair or timing claim follows.
The root handles publication after actual evidence review; no mail is sent.
