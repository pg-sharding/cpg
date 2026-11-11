# K4 layout comparison: five clean build inputs

Prepared locally for root review/transfer. No SSH, VM command, backend build or timing was performed by this subtask. Root owns launch, ordinary qualification and timing. Existing packets and source worktree/HEAD remain unchanged.

The capsule minimally adapts the proven K3 build harness. Sequence: **B, C, K3, K4, K4_assert**, with a deleted/recreated common-build for each variant. All builds reuse the identical common-source, common-build and compiled prefix paths; staged installs remain separate. Every build retains the unchanged core239 and posting-list checks,907 installed-header inventory, unchanged expected files and source inventory. Release objects outside access/gin must match B exactly. There is no observer.

| Source role | Canonical commit | Expected LP64 key size |
|---|---|---:|
| B | `8a8c475037bfde101da23cc9b0364c9c020eca93` | 152 |
| C | `af91ab8d13c4b7829ce2b3385d2072f55afc84f4` | 144 |
| K3 | `ec32d586cf3bb6cfa76eb672db70160b436ce47c` | 160 |
| K4 / K4_assert | `9d81c7ec4a3c27caeae1230b44f92bb5a8d47d3b` | 152 |

C is the baseline fixedB with exactly the same one-field nadditional reorder as K4, with no memo/cache. Its canonical root<localhost> commit was created once using an external index; only a new source branch was added. The .diff/.patch and receipt are included. K4 source is read from its existing canonical commit. All snapshots are obtained with git show, never generated independently per version. The existing fixedB prerequisite is reused unchanged.

`build-source/SOURCE.json` and the authentic7726-file B72 manifest describe every source snapshot. `common.source_plan` verifies all bytes, C's exact one-field reorder against B72's unchanged header, K4's same reorder against K3 and exact K3/K4 ginlogic identity. Fresh installed-header compile-only assertions check size, nrequired/additionalEntries/nadditional, entryRes, triConsistentFn, strategy and triCache where present. They run for all five builds, including K4_assert. These assertions are prospective; their runtime PASS is not claimed by local static review.

Flags remain the old matched flags: gcc, `-O2 -g -fno-lto`, `LDFLAGS=-fno-lto`, no ICU/readline, OpenSSL, release assertions off and final K4_assert on. Builds run nice10 with make-j2. Root should use its bounded launch wrapper and verify the available VM158 window. Local checks only parsed Python AST, exercised --help, verified the source plan and reviewed adaptations.

Transfer `build-inputs-K4-r1.tar.gz` into the root-owned namespace and extract its reviewed entries under `inputs/`. The existing authentic baseline archive was last bound in the D2 launch as `8c074fcf94a17d381e2df4a2b0554b925d76a777acb7e2f8a508abe7dfd2bbc4`; root rechecks it. The builder independently verifies its full extracted inventory before applying snapshots.

```sh
K4_ROOT=/home/reshke/allfuzz/gin-cache-k4-20261111
python3 -B "$K4_ROOT/inputs/build-harness/build.py" \
  --source-archive /home/reshke/allfuzz/gin-next-c11-bitmap-20261110/inputs/baseline.tar.gz \
  --source-plan "$K4_ROOT/inputs/build-source/SOURCE.json" \
  --output "$K4_ROOT/build-r1" --core-port 47100
```

Core ports47100..47104; posting-list check ports47130..47134. Output must be new/nonexistent. Each failed attempt is preserved, not overwritten or silently retried. Successful receipt status is `PASS_GIN_K4_LAYOUT_BUILDS`; role mapping B/T→B, C→C, K3→K3, K4→K4. Build success does not authorize timing. `checked_build` validates all five variants and their installed inventories for later root-owned stages.

Review changes before launch in `REVIEW-build.py.diff` and `REVIEW-common.py.diff`. The canonical C source commit generator is provenance only: do not rerun it on VM. The capsule contains no full baseline archive, clusters, binaries or existing runner logs.
