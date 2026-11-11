D3r2 fixed actual-backend decoder and complete SQL timing capsule — planned only

Fresh B/T/D2/D3, with B/T exactly one B prefix/ELF/native module and different fresh copies. D2 a85a9242f455b12c93528f3ace33eb69b6cd1008 and D3r2 1ce29c18ceb41882deced3ebe680ee75ba2c29b0 are independent alternatives over fixed B8a8c475037bfde101da23cc9b0364c9c020eca93. D3r1's actual helper-outlining/frame negative is retained separately and is never timed. R2 actual compile-only codegen inlines scalar decoding, retains separate segment loops and frame24, with larger1241byte main function versus D2844/B589. These are codegen observations, not speed results. Fresh full-backend normal ASM must also be reviewed before accepted timing.

No existing case is dropped: exact old18 allocation-inclusive native decoder definitions/loops and7 SQL records remain. Exactly3 prospectively declared native mixed cases are appended, all128items/20000loops: first delta2048 then126ones; first4ones then123delta2048; alternating2048,1 startinglong. Their expected compressed sizes are136/258/200bytes. They measure the explicit risk that long-first segments lose late dense batching, and dense-first segments retain mixed scalar dispatch. No new cutoff/sweep or outcome-based source/loop selection is permitted.

28cells×4roles×(2warm+12retained)×2freshcohorts =3136raw/2688retained/448warm. Smoke112commands/zeroaccepted. Twelve balanced Williams orders are the previous four-role base[0,1,3,2], four cyclic shifts repeated3; every position/directed adjacent pair balanced. Two fresh cohorts reverse case and physical copy placement, not independent machines. All6rolepairs,672absolutegroups/1008pairgroups/12096directroundpairs and planned87360 numerical comparisons. No pooling/trimming/repeat/control normalization/significance or causal attribution. All negatives and exact twin remain.

Actual helper is qualification/decoder-native.c compiled during qualification against each installed907headers/flags/ELF. Original compression/verifier/complete clock+benchmark body and old18 inputs are preserved; only deterministic generator cases and an untimed boundary oracle were added. The helper invokes the actual backend decoder. Native inner process CPU includes allocation, materialization and free; compression/full generated-output verification are outside that inner clock. Whole backend command schedstatCPU/clientwall remain separate. SQL primary is whole repeated-probe EXPLAIN ExecutionTime, not per-client-request latency. The seven SQL cells keep probes100/10/5/5/100/100/5, including Seq ID-only control with noGINcondition.

Campaign requires all4 fullbuild/core239/postingPASS, sourceplan59e277145711e1a3ad4ed3e942f9120c94203417071b0c3d27eda75634209007 and fixed build/qualification input hashes. Ordinary gate must pass21decoder+192mixed-boundary cases perrole and preserve old40SQL/7prepared/12lifecycle. Beforeprepare all5ordinary clusters stopped, source/fourinstalls/modules immutable. Prepare copies/fsyncs seed+all12numeric copies before roleassignment;4smoke and8unusedaccepted. Each stage preserves all25SQL orderedSeq/index comparisons perrole (100), not28SQL; new3cells are native. Every literal extra-warm and measured command/raw is durably saved before postchecks. Full semantic SQL plans/cardinality/rechecks, actual settings, decoder consumption/checksum and B/Tbindings remain mandatory. Smoke112 does not mean112accepted benchmarks.

Root-only after build/gate/codegen review (use separate options):

R=/home/reshke/allfuzz/gin-dec-d3-20261111
P="$R/inputs-full/timing-prep-r1/campaign.py"
python3 -B "$P" --stage prepare --build "$R/build-r1" --qualified "$R/qualification-r1" --output "$R/timing-r1" --first-port 48200 --cpu-pairs 0:4,4:0 --environment-label FRESH_HOST_CLEAN_SCREEN
python3 -B "$P" --stage smoke --build "$R/build-r1" --qualified "$R/qualification-r1" --output "$R/timing-r1" --first-port 48200 --cpu-pairs 0:4,4:0 --environment-label FRESH_HOST_CLEAN_SCREEN

STOP after smoke. Root independently reviews actual112rows/literals,100orderedcomparisons,7SQLsignatures/28settings, source/fullprefix/module/seed/unused8copies/PIDs/sockets/quietCPUtopology. Only its newly generated external PASS_SMOKE_REVIEW_FOR_FIXED_RUN receipt with freeze_sha256/smoke_status_sha256/environment_label permits:

python3 -B "$P" --stage run --build "$R/build-r1" --qualified "$R/qualification-r1" --output "$R/timing-r1" --first-port 48200 --cpu-pairs 0:4,4:0 --environment-label FRESH_HOST_CLEAN_SCREEN --review "$REVIEW"

Ports48200..3smoke/48210..7cohorts must be unused; sockets short underR/s. Root chooses/checks available distinct physical guestcores beforeprepare and freezes exactpairs (defaults0:4,4:0). Nice10/3GB apply to parent/children. Four own Unix-only servers share_buffers512MB/JITparallelautovacuumoff. No concurrentcompiler/profiler/timedjob. Sharedload label must be explicit beforefreeze; a clean label alone proves no quietwindow. PID/UID/ELF/datadir ownership checks precede signals, allfinallycleanup retained, no retries. Rawmonotonic clocks prove measured nonoverlap; literal realtime precedes measured realtimeend, while durableliteral-before-measure order follows runner source, not a reconstructed cross-clock start relation.

Local completion commands after rootcollection:
python3 -B analyze.py COLLECTED/cohort0 analysis0-new
python3 -B analyze.py COLLECTED/cohort1 analysis1-new
python3 -B audit-independent-r1.py --run-root COLLECTED --analysis0 analysis0-new --analysis1 analysis1-new --answers ../qualification/inputs/answers.json --out-new independent-new.json
python3 -B review-smoke-r1.py --timing-root COLLECTED --output smoke-recount-new.json

The independent auditor imports no runner/protocol/validator/analyzer; own integer TID/varbyte and statistics formulas check allraw/literals, schedule, full semanticSQL plans/settings, all6pairs and datahashes. Allread/write/fault/runqueue observations remain visible. Currentcapsule evidence is AST/help, protocol and independent integer-reference checking only; no new fullbuild/gate/smoke/timing executed during local preparation. Root alone imports/launches/collects/publishes.
