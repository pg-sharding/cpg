# Bounded heap SQL and actual-AM screen — preparation only

This new harness is minimally adapted from the completed C11 campaign. It
uses the qualified, unchanged B/Heap/Heap_assert builds and the stopped OR
runtime-r2 seed read-only. The production source remains
03dff8bfa5075e5838c7fbffc712d0b79d03f13d. This harness has not run on Linux;
static checks and help output are not runtime qualification.

The 12 cases are seven actual AM queries with 1/2/7/8/32/128/512 OR terms,
plus SQL controls for actual shared builtin-array entries at widths 8/32,
lossy OR8, absent512 and Seq. Each native dense union includes common and
returns 200,000 TIDs in one real scan. Index startup, allocation, heap setup
and remaining consistent work stay inside the loop clock. Tiny and threshold
7/8 controls expose startup and branch costs. No sparse full matrix is
promoted automatically.

The runtime-r2 qualification has independently proved actual builtin-array
sharing using matching private headers, pointer equality and entry counts;
tsquery multiqual alone does not share entries because its extra_data is
non-NULL. Timing SQL uses explicit pg_catalog.&& and requires a single real
GIN index condition containing both qualifiers. No private introspection or
modeled stream producer is part of measured AM calls.

B/T/Heap use exact B/T executable twins. Smoke is one placement with 36 warm
raw observations and zero retained. Screen requires separate approval after
smoke review: two fresh placements, two warm and six retained Williams
rounds, 576 raw / 432 retained / 144 warm. All six three-role permutations
are used. Source/ELF/seed/module/input bindings, clone-before-assignment,
durable raw full plans, all answers and owned cleanup follow the actual C11
driver. New SQL digests/scalars are frozen from the independently reviewed
fixture recipe. Original 25-case inputs and the AM module are unchanged.

Example smoke under a separately granted timing lease:

```sh
nice -n 10 python3 -B inputs/or/timing-r1/campaign.py \
  --build /home/reshke/allfuzz/gin-next-c11-bitmap-20261110/or-build \
  --qualified-from /home/reshke/allfuzz/gin-next-c11-bitmap-20261110/oq-r2 \
  --output /home/reshke/allfuzz/gin-next-c11-bitmap-20261110/os-r1 \
  --first-port 45600 --mode smoke
```

Collect the finite `review-smoke.py --list-files` allowlist and require the
offline reviewer PASS plus live stop/source/install checks. Screen uses the
same frozen files, `--mode screen` and a fresh short output such as `ot-r1`.
No compiler or other timing job may overlap. Preserve every negative,
absolute CPU/wall/executor/AM clock, spread and direct role pair without
trimming, normalization or pooling placements. This measures minimum
selection in the actual overall GIN work; it does not establish concurrency
qualification or make a new-algorithm claim.
