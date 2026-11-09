# GIN: advance V4 / lazy V4 full SQL comparison

Completed 10 November 2026 (+05:00): 25 cases, two fresh four-role cohorts,
2800 raw / 2400 retained / 400 warm observations, all ordinary answers equal.
Both alternatives give large selective SQL gains; repeated negative and
off-path control movements remain unresolved.

- [Results and limitations](RESULTS.md), [all 25 cases](results/ALL-RESULTS.md).
- [Repeat the build/setup/SQL experiment](REPRODUCE.md), [prospective protocol](PROTOCOL.md).
- [English unsent new-thread draft](email-draft-UNSENT.txt), [prior discussion](PRIOR-ART.md).
- [Advance diff](patches/advance-v4-over-fixed-base.diff),
  [lazy diff](patches/lazy-v4-over-fixed-base.diff): independent alternatives
  above [the common baseline](build-source/B/code-B72.diff), not a series.
- [Exact source plan](build-source/SOURCE.json),
  [code publication](CODE-PUBLICATION.json), `evidence/` for actual receipts/raw.

Baseline is exact B72 plus one common prerequisite, not current upstream
master. No candidate code changed in this wave. Four full builds each passed
original 239 core tests. All 13 ordinary clusters, measured processes and
sockets were stopped; source, installs, fixture and runtime identities passed
final checks. Local and remote independent recounts passed 13100 checks and
produced byte-identical Markdown/audit.

`harness/README.md` is retained verbatim as the prelaunch design note and is
part of the actual frozen inputs. Its old preparation status does not override
the completed execution receipts here. `REPRODUCE.md` is the current front door.
No new native-body or CREATE INDEX timings were taken; older measurements are
not presented as results of these fixed trees. The archive host was untouched.
