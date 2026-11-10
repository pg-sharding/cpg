# Bounded bitmap SQL and actual-AM screen — preparation only

This new harness is minimally adapted from the completed C11 campaign. It
uses the already qualified, unchanged B/Bitmap/Bitmap_assert builds and the
stopped bitmap qualification seed read-only. No new production source is
introduced. The frozen build and ordinary gate are separate prerequisites.
This harness has not run on Linux yet; AST, help and pure schedule checks do
not establish a runtime PASS.

There are exactly 12 cases: four prefix SQL targets (rare0, rare3, full and
low-memory lossy), the original inline/absent/OR/Seq SQL controls, and four
real index_rescan/index_getbitmap prefix AM cases. Prefix answers and row
digests come from the independent fixture recipe. All 25 original SQL
inputs/answers and the actual-AM module remain byte-identical to C11.

Roles are B/T/Bitmap, with exact B/T prefix and executable identity. A smoke
uses one fresh placement and one warm observation per role/case: 36 raw,
zero retained. Its reviewer has a finite collection allowlist. Only after a
separate review may screen mode run the fixed two placements, two warm and
six retained Williams rounds: 576 raw / 432 retained / 144 warm. All six
three-role permutations occur once per retained cycle. There is no automatic
promotion or repeat.

The campaign checks the old gate/build hashes and immutable seed/module,
copies/hashes/fsyncs every numeric clone before assignment, binds actual
backend ELFs/CPUs, records raw full plans before acceptance checks and stops
all three or six clusters. Full prefix lossy and index conditions must be
observed. Source/install/module/seed/input hashes are checked again at exit.
The original deadline, normal durability, 512 MB shared buffers and CPU 0/4
placements are retained. No builds or other timing job may overlap.

On the original leased VM, after source/host review, commands are:

```sh
nice -n 10 python3 -B inputs/bitmap/timing-r1/campaign.py \
  --build /home/reshke/allfuzz/gin-next-c11-bitmap-20261110/bitmap-build \
  --qualified-from /home/reshke/allfuzz/gin-next-c11-bitmap-20261110/bq-r1 \
  --output /home/reshke/allfuzz/gin-next-c11-bitmap-20261110/bs-r1 \
  --first-port 45500 --mode smoke
# Collect only review-smoke.py --list-files, review offline, then obtain
# the separately coordinated timing lease. Use a new output for screen.
```

`review-smoke.py --collection PATH --output-new NEW` checks actual smoke
answers, plans, hashes, twin identity and stop proofs. Run screen with the
same source/input bytes, `--mode screen`, and a fresh short output such as
`bt-r1`. All case/role/metric pairs and min/median/max/mean/sample SD/MAD are
retained separately for both placements. Small control differences and the
cost of materializing prefix TIDBitmaps must remain visible.

The separate 15-cell offset-fragment micro plan covers skip 0/1/2/4/large and
is not implemented or measured by this SQL/AM harness. It must remain labelled
as a fragment test, and cannot stand in for these actual AM/SQL measurements.
