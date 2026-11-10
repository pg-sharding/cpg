# Source provenance

The only new source edit restores the original transient comparison key shift from16 to32. It was authored once on C10 as C11 ca6ad39111cd67f20ff2dd3a8f619239d0360a10. An actual git cherry-pick -x onto P10 produced P11 a5e258877d0fcebc417c020351919a7e2706a7fe without a conflict. No per-branch source rewrite was used. Both incremental commits change one expression in gin_private.h; they preserve the four-byte memcpy and endian handling.

The fully built/timed source plan in this wave is B/P10/P11 plus P11_assert. C11 has release/assert production-unit and ordering preflight only. A full C11 build or C11 performance result must not be inferred. Earlier R1 sources and observations remain immutable. Complete candidate diffs after fixed B/C9 and incremental parent-relative diffs are alternative forms, not a patch series to apply twice.
