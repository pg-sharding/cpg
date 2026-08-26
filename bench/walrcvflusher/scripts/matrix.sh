#!/bin/bash
# matrix.sh — run all benchmark scenarios (S0-S11) for one build variant
#
# Usage:
#   ./matrix.sh <variant> [scenario_filter]
#
#   variant       — "baseline" (git checkout d68f87caf9f) or "new" (git checkout 69cf50b2dac)
#   scenario_filter — optional; run only scenarios matching this pattern (e.g. "S0", "S2", "S5")
#
# Prerequisites:
#   1. Build PostgreSQL:  make -j install
#   2. Build throttle:    gcc -shared -fPIC -o work/fsync_throttle.so scripts/fsync_throttle.c -ldl
#   3. ./setup.sh            (for non-cascade scenarios)
#   4. ./cascade_setup.sh     (for S7; run separately)
#
# Example:
#   ./matrix.sh new          # run all scenarios for the new build
#   ./matrix.sh baseline S0  # run only S0 for baseline
#

source "$(dirname "$0")/common.sh"

VARIANT="${1:?Usage: matrix.sh <baseline|new> [scenario_filter]}"
FILTER="${2:-}"

# Results CSV header
echo "label,wal_recv_bps,wal_delta_bytes,elapsed_sec" > "$RESULTS_DIR/ALL.csv"

# ── Helper: run one scenario N times ──────────────────────────────────────────
run_scenario() {
    local label="$1"
    shift
    # Skip if filter doesn't match
    if [ -n "$FILTER" ] && ! echo "$label" | grep -q "$FILTER"; then
        log "Skipping $label (filter: $FILTER)"
        return
    fi
    log "=== Scenario: $label ==="
    for i in $(seq 1 "$RUNS"); do
        local run_label="${label}_run${i}"
        "$SCRIPTS_DIR/run_bench.sh" "$run_label" "$@"
    done
}

# ── Helper: change sync rep settings ──────────────────────────────────────────
set_sync_rep() {
    local mode="$1"
    if [ "$mode" = "off" ]; then
        psql_p "ALTER SYSTEM SET synchronous_standby_names = '';" 2>/dev/null
        psql_p "ALTER SYSTEM SET synchronous_commit = 'off';" 2>/dev/null
    elif [ "$mode" = "remote_flush" ]; then
        psql_p "ALTER SYSTEM SET synchronous_standby_names = '1';" 2>/dev/null
        psql_p "ALTER SYSTEM SET synchronous_commit = 'remote_flush';" 2>/dev/null
    elif [ "$mode" = "remote_write" ]; then
        psql_p "ALTER SYSTEM SET synchronous_standby_names = '1';" 2>/dev/null
        psql_p "ALTER SYSTEM SET synchronous_commit = 'remote_write';" 2>/dev/null
    fi
    psql_p "SELECT pg_reload_conf();" >/dev/null 2>&1
    sleep 2
}

# ── Prepare tables for custom scripts ────────────────────────────────────────
log "Preparing tables for custom pgbench scripts..."
psql_p -f "$SQL_DIR/prepare_tables.sql" 2>/dev/null || true

# ═══════════════════════════════════════════════════════════════════════════════
# S0 — Baseline TPC-B (reference, no throttle)
# ═══════════════════════════════════════════════════════════════════════════════
run_scenario "${VARIANT}_S0_tpcb" --builtin=tpcb --client=32 --jobs=8

# ═══════════════════════════════════════════════════════════════════════════════
# S1 — Fast disk control (TPC-B, no throttle — fsync should not be bottleneck)
#      Same as S0 but explicitly labelled for comparison with S2
# ═══════════════════════════════════════════════════════════════════════════════
run_scenario "${VARIANT}_S1_fast" --builtin=tpcb --client=32 --jobs=8

# ═══════════════════════════════════════════════════════════════════════════════
# S2 — Slow disk simulation (restart standby with throttle)
#      Requires: THROTTLE_MS set and standby restarted with LD_PRELOAD
#      Run manually: ./setup.sh throttle && THROTTLE_MS=20 ./matrix.sh variant S2
# ═══════════════════════════════════════════════════════════════════════════════
if [ "${THROTTLE_MS:-0}" -gt 0 ]; then
    log "S2: Running with THROTTLE_MS=$THROTTLE_MS"
    run_scenario "${VARIANT}_S2_throttle${THROTTLE_MS}" --builtin=tpcb --client=32 --jobs=8
else
    log "S2: Skipped (set THROTTLE_MS>0 and run: ./setup.sh throttle && THROTTLE_MS=20 $0 $VARIANT S2)"
fi

# ═══════════════════════════════════════════════════════════════════════════════
# S3 — High WAL rate (small transactions)
# ═══════════════════════════════════════════════════════════════════════════════
run_scenario "${VARIANT}_S3_smalltx" -f "$SQL_DIR/smalltx.sql" --client=64 --no-vacuum

# ═══════════════════════════════════════════════════════════════════════════════
# S4 — Large transactions (bulk COPY-like)
# ═══════════════════════════════════════════════════════════════════════════════
run_scenario "${VARIANT}_S4_bulk" -f "$SQL_DIR/copy_bulk.sql" --client=1 --no-vacuum

# ═══════════════════════════════════════════════════════════════════════════════
# S5 — Synchronous replication remote_flush
#      Commit on primary waits for flush_lsn on standby (now done by flusher)
# ═══════════════════════════════════════════════════════════════════════════════
set_sync_rep "remote_flush"
wait_for_streaming "$PRIMARY_PORT" "standby1"
run_scenario "${VARIANT}_S5_remoteflush" --builtin=tpcb --client=32 --jobs=8
set_sync_rep "off"

# ═══════════════════════════════════════════════════════════════════════════════
# S6 — Synchronous replication remote_write
#      Commit waits only for write_lsn (should not depend on flusher)
# ═══════════════════════════════════════════════════════════════════════════════
set_sync_rep "remote_write"
wait_for_streaming "$PRIMARY_PORT" "standby1"
run_scenario "${VARIANT}_S6_remotewrite" --builtin=tpcb --client=32 --jobs=8
set_sync_rep "off"

# ═══════════════════════════════════════════════════════════════════════════════
# S7 — Cascade replication (requires ./cascade_setup.sh first)
#      primary → replica1 → replica2
#      NOTE: This scenario uses different ports (CASC1_PORT, CASC2_PORT)
#      Run separately after: ./cascade_setup.sh && ./run_bench.sh "${VARIANT}_S7_cascade"
# ═══════════════════════════════════════════════════════════════════════════════
log "S7: Cascade scenario — run separately:"
log "  ./cascade_setup.sh && ./run_bench.sh ${VARIANT}_S7_cascade --builtin=tpcb --client=32 --jobs=8"
log "  Then collect lag on both casc1 and casc2."

# ═══════════════════════════════════════════════════════════════════════════════
# S8 — Different wal_segment_size (requires re-init)
#      NOTE: Run separately with WAL_SEG_SIZE=1 or WAL_SEG_SIZE=256
#      Example: WAL_SEG_SIZE=1 ./setup.sh && ./matrix.sh variant S8
# ═══════════════════════════════════════════════════════════════════════════════
run_scenario "${VARIANT}_S8_seg${WAL_SEG_SIZE}" --builtin=tpcb --client=32 --jobs=8

# ═══════════════════════════════════════════════════════════════════════════════
# S9 — WAL-heavy (UPDATE + INSERT, full-page images)
# ═══════════════════════════════════════════════════════════════════════════════
run_scenario "${VARIANT}_S9_walheavy" -f "$SQL_DIR/walheavy.sql" --client=32 --no-vacuum

# ═══════════════════════════════════════════════════════════════════════════════
# S10 — Commit isolation (run with different git checkouts separately)
#       To isolate contributions of d68f87caf9f (replay-before-flush)
#       and 69cf50b2dac (flusher process), run:
#         git checkout d68f87caf9f~1 && make install && ./matrix.sh pre_d68 S0
#         git checkout d68f87caf9f   && make install && ./matrix.sh d68     S0
#         git checkout 69cf50b2dac   && make install && ./matrix.sh new     S0
# ═══════════════════════════════════════════════════════════════════════════════
log "S10: Commit isolation — run manually with 3 git checkouts (see README)"

# ═══════════════════════════════════════════════════════════════════════════════
# S11 — recovery_min_apply_delay (apply stress)
#       WAL accumulates on standby; check flusher doesn't interact badly
# ═══════════════════════════════════════════════════════════════════════════════
psql_s "ALTER SYSTEM SET recovery_min_apply_delay = '5s';" 2>/dev/null
psql_s "SELECT pg_reload_conf();" 2>/dev/null
sleep 2
run_scenario "${VARIANT}_S11_delay5s" --builtin=tpcb --client=32 --jobs=8
psql_s "ALTER SYSTEM SET recovery_min_apply_delay = '0';" 2>/dev/null
psql_s "SELECT pg_reload_conf();" 2>/dev/null

log "============================================"
log "Matrix complete for variant: $VARIANT"
log "Results: $RESULTS_DIR/ALL.csv"
log "Per-run details: $RESULTS_DIR/${VARIANT}_*/"
log "============================================"
