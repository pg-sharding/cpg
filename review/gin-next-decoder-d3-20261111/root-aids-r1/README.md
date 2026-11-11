D3 root-executed collection and live-proof helpers

These scripts are outside the frozen source/build/qualification/timing capsules. Local AST/help passed; no SSH, server, build, live inspection or benchmark was executed by the child. Root reviews and executes them in the owned gin-dec-d3-20261111 namespace. Do not run collection or hashing during accepted timings.

Example commands after each corresponding stage passes (H is this extracted helper directory):

R=/home/reshke/allfuzz/gin-dec-d3-20261111
H="$R/root-aids-r1"
python3 -B "$H/live-proof.py" --root "$R" --stage qualification --output "$R/ROOT-LIVE-QUALIFICATION-D3-r1.json"
python3 -B "$H/collect.py" --root "$R" --stage qualification --output "$R/selected-qualification-r1.tar.gz"

After timing inputs are imported and the host/CPU topology is reviewed, the optional controller only prepares and runs the zero-accepted smoke:

python3 -B "$H/run-stages.py" --root "$R" --cpu-pairs 0:4,4:0 --environment-label FRESH_HOST_CLEAN_SCREEN
python3 -B "$H/live-proof.py" --root "$R" --stage smoke --controller-pid ACTUAL_COMPLETED_PREPARE_SMOKE_PID --output "$R/ROOT-LIVE-SMOKE-D3-r1.json"
python3 -B "$H/collect.py" --root "$R" --stage smoke --output "$R/selected-smoke-r1.tar.gz"

Stop for independent actual112-row smoke and live review. This controller has no accepted-run option. It verifies exact three capsule manifests, uses nice10 and inherited 3 GB address space, two bounded 1800-second stages and TERM cleanup grace480. A clean label requires load1<2 before stages; root must still check the actual quiet window and known other jobs. Failures are preserved without automatic retry.

After the separately approved fixed run and its controller exit:

python3 -B "$H/live-proof.py" --root "$R" --stage full --controller-pid ACTUAL_COMPLETED_ACCEPTED_RUN_PID --output "$R/ROOT-LIVE-FINAL-D3-r1.json"
python3 -B "$H/collect.py" --root "$R" --stage full --output "$R/selected-full-r1.tar.gz"

live-proof.py is read-only apart from its new JSON receipt. It checks four installed prefixes/907 headers, all7726 source files, exact input manifests, normal ASM bindings, native modules, seeds and expected5/9/17 recorded cluster lifetimes. Smoke checks all8 untouched accepted copies; full checks3136/2688/448 and both1568/1344 cohort hashes. Known recorded PIDs/sockets must be absent. It never signals, scans foreign processes or reads foreign /proc/exe. Pass actual known controller PID arguments; a reused/non-absent PID conservatively fails and requires root review.

collect.py only reads selected JSON/JSONL, actual normal full-TU ASM, native raw/results, command metadata and last80 lines of core/posting test summaries. It includes build/status.json (the earlier D2 omission is not repeated). Each original file is UTF-8/NUL-free, below8MiB; total below64MiB and600 members. No PGDATA, ELF, object, .so, source archive or complete runner/build log is selected. A SHA/size collection manifest includes hashes for bounded derived test tails. The resulting transfer tar is not itself a publication payload; root extracts and verifies selected text and excludes the archive later. Existing negative codegen evidence is already collected locally and remains separate.
