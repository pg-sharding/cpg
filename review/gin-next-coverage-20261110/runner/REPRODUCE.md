# Reproduce the ordinary write/build controls

This runner is newly prepared. Consult its runtime status before describing
it as tested. Static preflight alone is not a benchmark result.

Use Linux x86-64 with Python 3, taskset/lscpu from util-linux and the build
dependencies declared by `../c11-bitmap/c11/build-harness/README.md`. Rebuild
the pinned B/C9/C10/C11/C11_assert variants using that packet. Exact revisions,
flags, installed-tree hashes, core tests and posting-list checks are carried
by its build receipt. No system PostgreSQL installation is altered.

Run that packet's `campaign.py --mode qualify` first, and require PASS with
empty cleanup_errors. Qualification creates and cleanly stops the source
fixture. This harness consumes it read-only and creates fresh private copies.
Keep the build, qualification and harness paths accessible on the same host.

```sh
python3 -B /absolute/coverage/operations.py --operation create-index \
  --build /absolute/build-r1 --qualified-from /absolute/qualify-r1 \
  --output /absolute/new-create-index-r1 --first-port 45700
python3 -B /absolute/coverage/operations.py --operation insert \
  --build /absolute/build-r1 --qualified-from /absolute/qualify-r1 \
  --output /absolute/new-insert-r1 --first-port 45700
python3 -B /absolute/coverage/operations.py --operation vacuum \
  --build /absolute/build-r1 --qualified-from /absolute/qualify-r1 \
  --output /absolute/new-vacuum-r1 --first-port 45700
```

Run commands sequentially on an otherwise unleased test VM, as a non-root
user. Output directories must not exist. CPUs 0 and 4 must be available and
belong to distinct physical cores, as on our declared test VMs; preserve the
recorded topology. Keep output paths short: the absolute socket path must fit
the helper's enforced 104-byte limit. Ports are Unix-only;
the clusters do not listen on TCP.

Each output includes protocol, input/source identities, role mapping, raw
JSONL, absolute and paired tables, qualification answers and stop receipts.
Only PASS with empty cleanup_errors is a completed run. Preserve failed
attempts separately and use a new output directory for a corrected rerun.
Do not publish PGDATA, binaries, complete runner logs or private mail data.
