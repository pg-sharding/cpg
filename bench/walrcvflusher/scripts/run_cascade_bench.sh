#!/bin/bash
# run_cascade_bench.sh — cascade replication benchmark
#
# Topology: primary → casc1 (throttled) → casc2
#
# The key insight: in cascade, casc1 must both:
#   1. fsync its own WAL (throttled = slow)
#   2. forward WAL to casc2
#
# With flusher: casc1's walreceiver is free from fsync and can
#   forward WAL to casc2 immediately after write().
# Without flusher: casc1's walreceiver blocks on fsync before
#   advancing flushedUpto, delaying WAL forwarding to casc2.
#
# So we expect: casc2 lag (replay_lag) should be lower with flusher.
#
# Usage:  ./run_cascade_bench.sh <variant> [throttle_ms] [pgbench_args...]
#   variant     — "baseline" or "new"
#   throttle_ms — fsync delay on casc1 (default: 50)
#
# Example:
#   ./run_cascade_bench.sh new 50
#   ./run_cascade_bench.sh baseline 50

source "$(dirname "$0")/common.sh"

VARIANT="${1:?Usage: run_cascade_bench.sh <baseline|new> [throttle_ms]}"
THROTTLE_MS_VAL="${2:-50}"

LABEL="${VARIANT}_cascade${THROTTLE_MS_VAL}"
OUT="$RESULTS_DIR/$LABEL"
mkdir -p "$OUT"

export THROTTLE_MS="$THROTTLE_MS_VAL"

# ── Setup cascade ────────────────────────────────────────────────────────────
log "=== $LABEL: setting up cascade (throttle=${THROTTLE_MS}ms on casc1) ==="

if [ "$THROTTLE_MS_VAL" -eq 0 ]; then
    ./scripts/cascade_setup.sh 2>&1 | tail -3
else
    ./scripts/cascade_setup.sh throttle 2>&1 | tail -3
fi

# Init pgbench tables on primary
log "[$LABEL] Initializing pgbench tables..."
pgbench -i -p "$PRIMARY_PORT" -d postgres >/dev/null 2>&1
sleep 5  # let cascade catch up

# Reset IO stats on both standbys
reset_io_stats "$CASC1_PORT"
reset_io_stats "$CASC2_PORT"

# ── Start LSN on casc2 (the end of the chain) ─────────────────────────────────
START_LSN_C2=$(psql_c2 "SELECT pg_last_wal_replay_lsn()")
START_LSN_C1=$(psql_c1 "SELECT pg_last_wal_replay_lsn()")
START_TS=$(date +%s.%N)

# ── Background lag collector (every 2s) ──────────────────────────────────────
# Collect lag from primary→casc1 and casc1→casc2
( while true; do
    # primary → casc1 lag
    P_C1=$(psql -p "$PRIMARY_PORT" -d postgres -At -c \
      "SELECT clock_timestamp()||',primary_to_casc1,'||coalesce(flush_lag::text,'')||','||coalesce(replay_lag::text,'') FROM pg_stat_replication WHERE application_name='casc1'" 2>/dev/null)
    echo "$P_C1" >> "$OUT/lag_primary_casc1.csv" 2>/dev/null

    # casc1 → casc2 lag
    C1_C2=$(psql -p "$CASC1_PORT" -d postgres -At -c \
      "SELECT clock_timestamp()||',casc1_to_casc2,'||coalesce(flush_lag::text,'')||','||coalesce(replay_lag::text,'') FROM pg_stat_replication WHERE application_name='casc2'" 2>/dev/null)
    echo "$C1_C2" >> "$OUT/lag_casc1_casc2.csv" 2>/dev/null

    sleep 2
done ) &
LAG_PID=$!

# ── pgbench run ──────────────────────────────────────────────────────────────
log "[$LABEL] Running pgbench for ${DURATION}s (TPC-B, 32 clients)..."
pgbench -p "$PRIMARY_PORT" -d postgres --no-vacuum --time="$DURATION" \
    --client=32 --jobs=8 > "$OUT/pgbench.log" 2>&1

# ── End LSN ──────────────────────────────────────────────────────────────────
END_TS=$(date +%s.%N)
END_LSN_C2=$(psql_c2 "SELECT pg_last_wal_replay_lsn()")
END_LSN_C1=$(psql_c1 "SELECT pg_last_wal_replay_lsn()")

# Stop lag collector
kill $LAG_PID 2>/dev/null; wait 2>/dev/null

# ── Compute metrics ──────────────────────────────────────────────────────────
ELAPSED=$(echo "$END_TS - $START_TS" | bc -l)

# WAL rate at casc1 (how fast casc1 receives)
WAL_DELTA_C1=$(psql_c1 "SELECT pg_wal_lsn_diff('$END_LSN_C1','$START_LSN_C1')::bigint")
WAL_BPS_C1=$(echo "scale=0; $WAL_DELTA_C1 / $ELAPSED" | bc -l)

# WAL rate at casc2 (how fast casc2 receives — end of chain)
WAL_DELTA_C2=$(psql_c2 "SELECT pg_wal_lsn_diff('$END_LSN_C2','$START_LSN_C2')::bigint")
WAL_BPS_C2=$(echo "scale=0; $WAL_DELTA_C2 / $ELAPSED" | bc -l)

# TPS
TPS=$(grep "tps =" "$OUT/pgbench.log" | head -1 | sed 's/.*tps = //' | sed 's/ .*//')

# ── pg_stat_io on casc1 (the throttled middle node) ──────────────────────────
psql -p "$CASC1_PORT" -d postgres -c "
SELECT backend_type, object, context,
       reads, writes, writebacks, fsyncs, extends,
       read_time, write_time, writeback_time, fsync_time
FROM pg_stat_io
WHERE backend_type IN ('walreceiver','walrcvflusher','startup','checkpointer')
  AND object = 'wal'
ORDER BY backend_type, context;" > "$OUT/pg_stat_io_casc1.txt" 2>&1

# fsync timing on casc1
psql -p "$CASC1_PORT" -d postgres -c "
SELECT backend_type, fsyncs,
       round(fsync_time::numeric / greatest(fsyncs,1), 3) AS avg_fsync_ms,
       fsync_time AS total_fsync_ms
FROM pg_stat_io
WHERE object = 'wal'
  AND backend_type IN ('walreceiver','walrcvflusher')
ORDER BY backend_type;" > "$OUT/fsync_timing_casc1.txt" 2>&1

# ── pg_stat_io on casc2 (end of chain) ────────────────────────────────────────
psql -p "$CASC2_PORT" -d postgres -c "
SELECT backend_type, object, context,
       reads, writes, writebacks, fsyncs, extends,
       read_time, write_time, writeback_time, fsync_time
FROM pg_stat_io
WHERE backend_type IN ('walreceiver','walrcvflusher','startup','checkpointer')
  AND object = 'wal'
ORDER BY backend_type, context;" > "$OUT/pg_stat_io_casc2.txt" 2>&1

# ── pg_stat_replication (both hops) ───────────────────────────────────────────
psql -p "$PRIMARY_PORT" -d postgres -c "
SELECT application_name, state, sync_state,
       sent_lsn, write_lsn, flush_lsn, replay_lsn,
       write_lag, flush_lag, replay_lag
FROM pg_stat_replication;" > "$OUT/pg_stat_replication_primary.txt" 2>&1

psql -p "$CASC1_PORT" -d postgres -c "
SELECT application_name, state, sync_state,
       sent_lsn, write_lsn, flush_lsn, replay_lsn,
       write_lag, flush_lag, replay_lag
FROM pg_stat_replication;" > "$OUT/pg_stat_replication_casc1.txt" 2>&1

# ── Extract fsync counts from casc1 ──────────────────────────────────────────
FLUSHER_FSYNCS=$(psql_c1 "SELECT coalesce(sum(fsyncs),0) FROM pg_stat_io WHERE object='wal' AND backend_type='walrcvflusher'" 2>/dev/null)
FLUSHER_FSYNC_TIME=$(psql_c1 "SELECT coalesce(sum(fsync_time),0) FROM pg_stat_io WHERE object='wal' AND backend_type='walrcvflusher'" 2>/dev/null)
WALRCV_FSYNCS=$(psql_c1 "SELECT coalesce(sum(fsyncs),0) FROM pg_stat_io WHERE object='wal' AND backend_type='walreceiver'" 2>/dev/null)
WALRCV_FSYNC_TIME=$(psql_c1 "SELECT coalesce(sum(fsync_time),0) FROM pg_stat_io WHERE object='wal' AND backend_type='walreceiver'" 2>/dev/null)

# ── Summary ──────────────────────────────────────────────────────────────────
echo "label=$LABEL throttle_ms=$THROTTLE_MS_VAL elapsed=${ELAPSED}s" \
    | tee "$OUT/summary.txt"
echo "wal_bps_casc1=$WAL_BPS_C1 wal_bps_casc2=$WAL_BPS_C2 tps=$TPS" \
    | tee -a "$OUT/summary.txt"
echo "casc1_flusher_fsyncs=$FLUSHER_FSYNCS casc1_flusher_fsync_time=${FLUSHER_FSYNC_TIME}ms" \
    | tee -a "$OUT/summary.txt"
echo "casc1_walrcv_fsyncs=$WALRCV_FSYNCS casc1_walrcv_fsync_time=${WALRCV_FSYNC_TIME}ms" \
    | tee -a "$OUT/summary.txt"

# CSV row
echo "$LABEL,$VARIANT,$THROTTLE_MS_VAL,$ELAPSED,$WAL_BPS_C1,$WAL_BPS_C2,$TPS,$FLUSHER_FSYNCS,$FLUSHER_FSYNC_TIME,$WALRCV_FSYNCS,$WALRCV_FSYNC_TIME" \
    >> "$RESULTS_DIR/cascade_matrix.csv"

log "[$LABEL] Done: wal_bps_casc1=$WAL_BPS_C1 wal_bps_casc2=$WAL_BPS_C2 tps=$TPS"
log "  casc1: flusher_fsyncs=$FLUSHER_FSYNCS(${FLUSHER_FSYNC_TIME}ms) walrcv_fsyncs=$WALRCV_FSYNCS(${WALRCV_FSYNC_TIME}ms)"
