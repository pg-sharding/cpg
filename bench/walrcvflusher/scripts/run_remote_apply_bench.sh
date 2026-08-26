#!/bin/bash
# run_remote_apply_bench.sh — synchronous_commit=remote_apply benchmark
#
# With remote_apply, primary waits for standby to fully replay (apply) each
# transaction before acknowledging commit. This tests whether the flusher
# helps by decoupling flush from apply — if replay can proceed before flush
# completes, remote_apply latency should be lower.
#
# Usage:  ./run_remote_apply_bench.sh <variant> [throttle_ms] [clients] [duration]
#   variant     — "baseline" or "new"
#   throttle_ms — fsync delay on standby (default: 50)
#   clients     — pgbench clients (default: 32)
#   duration    — seconds (default: 30)

source "$(dirname "$0")/common.sh"

VARIANT="${1:?Usage: run_remote_apply_bench.sh <baseline|new> [throttle_ms] [clients] [duration]}"
THROTTLE_MS_VAL="${2:-50}"
CLIENTS="${3:-32}"
DURATION="${4:-30}"

LABEL="${VARIANT}_remote_apply${THROTTLE_MS_VAL}_c${CLIENTS}"
OUT="$RESULTS_DIR/$LABEL"
mkdir -p "$OUT"

export THROTTLE_MS="$THROTTLE_MS_VAL"

# ── Setup ────────────────────────────────────────────────────────────────────
log "=== $LABEL: setup (throttle=${THROTTLE_MS}ms, clients=$CLIENTS, duration=${DURATION}s) ==="

if [ "$THROTTLE_MS_VAL" -eq 0 ]; then
    ./scripts/setup.sh 2>&1 | tail -2
else
    ./scripts/setup.sh throttle 2>&1 | tail -2
fi

# ── Enable synchronous replication with remote_apply ─────────────────────────
log "[$LABEL] Enabling synchronous_commit=remote_apply..."
psql_p "ALTER SYSTEM SET synchronous_standby_names = '*';"
psql_p "ALTER SYSTEM SET synchronous_commit = remote_apply;"
psql_p "SELECT pg_reload_conf();"
sleep 2

# Verify sync state
SYNC_STATE=$(psql_p "SELECT sync_state FROM pg_stat_replication WHERE application_name='standby1'")
log "[$LABEL] sync_state=$SYNC_STATE"

# ── Prepare tables for walheavy ──────────────────────────────────────────────
psql_p "CREATE TABLE IF NOT EXISTS accounts(aid integer PRIMARY KEY, abalance integer);"
psql_p "CREATE TABLE IF NOT EXISTS audit(aid integer, ts timestamptz);"
psql_p "INSERT INTO accounts SELECT i, 0 FROM generate_series(1, 1000) i ON CONFLICT DO NOTHING;"
psql_p "TRUNCATE audit;"
psql_p "CHECKPOINT;"
sleep 3

# Reset IO stats
reset_io_stats "$PRIMARY_PORT"
reset_io_stats "$STANDBY_PORT"

# ── Start LSN ────────────────────────────────────────────────────────────────
START_LSN=$(psql_s "SELECT pg_last_wal_replay_lsn()")
START_TS=$(date +%s.%N)

# ── Background lag collector (every 2s) ──────────────────────────────────────
( while true; do
    psql -p "$PRIMARY_PORT" -d postgres -At -c \
      "SELECT clock_timestamp()||','||application_name||','||coalesce(flush_lag::text,'')||','||coalesce(replay_lag::text,'') FROM pg_stat_replication WHERE application_name='standby1'"
    >> "$OUT/lag.csv" 2>/dev/null
    sleep 2
done ) &
LAG_PID=$!

# ── pgbench run: walheavy ────────────────────────────────────────────────────
log "[$LABEL] Running pgbench (walheavy): $CLIENTS clients, ${DURATION}s..."
pgbench -p "$PRIMARY_PORT" -d postgres --no-vacuum \
    -f "$SQL_DIR/walheavy.sql" \
    --client="$CLIENTS" --jobs=4 \
    --time="$DURATION" \
    > "$OUT/pgbench.log" 2>&1

# ── End ──────────────────────────────────────────────────────────────────────
END_TS=$(date +%s.%N)
END_LSN=$(psql_s "SELECT pg_last_wal_replay_lsn()")

# Stop lag collector
kill $LAG_PID 2>/dev/null; wait 2>/dev/null

# Wait for pgstat flush
log "[$LABEL] Waiting 10s for pgstat flush..."
sleep 10

# ── Compute metrics ──────────────────────────────────────────────────────────
ELAPSED=$(echo "$END_TS - $START_TS" | bc -l)
WAL_DELTA=$(psql_p "SELECT pg_wal_lsn_diff('$END_LSN','$START_LSN')::bigint")
WAL_BPS=$(echo "scale=0; $WAL_DELTA / $ELAPSED" | bc -l)
WAL_DELTA_HR=$(psql_p "SELECT pg_size_pretty($WAL_DELTA::bigint)")

# TPS from pgbench
TPS=$(grep "tps =" "$OUT/pgbench.log" 2>/dev/null | head -1 || echo "tps = N/A")

# ── pg_stat_io snapshot ──────────────────────────────────────────────────────
psql -p "$STANDBY_PORT" -d postgres -c "
SELECT backend_type, object, context,
       reads, writes, writebacks, fsyncs, extends,
       read_time, write_time, writeback_time, fsync_time
FROM pg_stat_io
WHERE backend_type IN ('walreceiver','walrcvflusher','startup','checkpointer')
  AND object = 'wal'
ORDER BY backend_type, context;" > "$OUT/pg_stat_io.txt" 2>&1

FLUSHER_FSYNCS=$(psql_s "SELECT coalesce(sum(fsyncs),0) FROM pg_stat_io WHERE object='wal' AND backend_type='walrcvflusher'" 2>/dev/null)
FLUSHER_FSYNC_TIME=$(psql_s "SELECT coalesce(sum(fsync_time),0) FROM pg_stat_io WHERE object='wal' AND backend_type='walrcvflusher'" 2>/dev/null)
WALRCV_FSYNCS=$(psql_s "SELECT coalesce(sum(fsyncs),0) FROM pg_stat_io WHERE object='wal' AND backend_type='walreceiver'" 2>/dev/null)
WALRCV_FSYNC_TIME=$(psql_s "SELECT coalesce(sum(fsync_time),0) FROM pg_stat_io WHERE object='wal' AND backend_type='walreceiver'" 2>/dev/null)

# ── pg_stat_replication ──────────────────────────────────────────────────────
psql -p "$PRIMARY_PORT" -d postgres -c "
SELECT application_name, state, sync_state,
       sent_lsn, write_lsn, flush_lsn, replay_lsn,
       write_lag, flush_lag, replay_lag
FROM pg_stat_replication;" > "$OUT/pg_stat_replication.txt" 2>&1

# ── Summary ──────────────────────────────────────────────────────────────────
echo "label=$LABEL throttle_ms=$THROTTLE_MS_VAL clients=$CLIENTS elapsed=${ELAPSED}s" \
    | tee "$OUT/summary.txt"
echo "wal_delta=$WAL_DELTA_HR wal_recv_bps=$WAL_BPS" \
    | tee -a "$OUT/summary.txt"
echo "pgbench: $TPS" \
    | tee -a "$OUT/summary.txt"
echo "flusher_fsyncs=$FLUSHER_FSYNCS flusher_fsync_time=${FLUSHER_FSYNC_TIME}ms" \
    | tee -a "$OUT/summary.txt"
echo "walrcv_fsyncs=$WALRCV_FSYNCS walrcv_fsync_time=${WALRCV_FSYNC_TIME}ms" \
    | tee -a "$OUT/summary.txt"

# CSV
echo "$LABEL,$VARIANT,remote_apply,$THROTTLE_MS_VAL,$CLIENTS,$ELAPSED,$WAL_BPS,$WAL_DELTA,$FLUSHER_FSYNCS,$FLUSHER_FSYNC_TIME,$WALRCV_FSYNCS,$WALRCV_FSYNC_TIME" \
    >> "$RESULTS_DIR/remote_apply_matrix.csv"

log "[$LABEL] Done: wal_recv_bps=$WAL_BPS ($WAL_DELTA_HR in ${ELAPSED}s)"
log "  flusher: $FLUSHER_FSYNCS fsyncs (${FLUSHER_FSYNC_TIME}ms)"
log "  walrcv:  $WALRCV_FSYNCS fsyncs (${WALRCV_FSYNC_TIME}ms)"
