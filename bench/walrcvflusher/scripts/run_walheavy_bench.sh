#!/bin/bash
# run_walheavy_bench.sh — high WAL benchmark with full-page images
#
# Uses walheavy.sql (UPDATE + INSERT bulk) to generate heavy WAL with FPI.
# Run with CHECKPOINT before benchmark to maximize FPI generation.
#
# Usage:  ./run_walheavy_bench.sh <variant> [throttle_ms] [mode] [clients] [duration]
#   variant     — "baseline" or "new"
#   throttle_ms — fsync delay on standby (default: 50)
#   mode        — "2node" (default) or "cascade"
#   clients     — pgbench clients (default: 32)
#   duration    — seconds (default: 30)
#
# Example:
#   ./run_walheavy_bench.sh new 50
#   ./run_walheavy_bench.sh baseline 50 cascade 64 60

source "$(dirname "$0")/common.sh"

VARIANT="${1:?Usage: run_walheavy_bench.sh <baseline|new> [throttle_ms] [2node|cascade] [clients] [duration]}"
THROTTLE_MS_VAL="${2:-50}"
MODE="${3:-2node}"
CLIENTS="${4:-32}"
DURATION="${5:-30}"

if [ "$MODE" = "cascade" ]; then
    LABEL="${VARIANT}_walheavy_cascade${THROTTLE_MS_VAL}_c${CLIENTS}"
else
    LABEL="${VARIANT}_walheavy${THROTTLE_MS_VAL}_c${CLIENTS}"
fi
OUT="$RESULTS_DIR/$LABEL"
mkdir -p "$OUT"

export THROTTLE_MS="$THROTTLE_MS_VAL"

# ── Setup ────────────────────────────────────────────────────────────────────
log "=== $LABEL: setup (mode=$MODE, throttle=${THROTTLE_MS}ms, clients=$CLIENTS, duration=${DURATION}s) ==="

if [ "$MODE" = "cascade" ]; then
    if [ "$THROTTLE_MS_VAL" -eq 0 ]; then
        ./scripts/cascade_setup.sh 2>&1 | tail -3
    else
        ./scripts/cascade_setup.sh throttle 2>&1 | tail -3
    fi
else
    if [ "$THROTTLE_MS_VAL" -eq 0 ]; then
        ./scripts/setup.sh 2>&1 | tail -2
    else
        ./scripts/setup.sh throttle 2>&1 | tail -2
    fi
fi

# ── Prepare tables ────────────────────────────────────────────────────────────
log "[$LABEL] Preparing tables..."
psql_p "CREATE TABLE IF NOT EXISTS accounts(aid integer PRIMARY KEY, abalance integer);"
psql_p "CREATE TABLE IF NOT EXISTS audit(aid integer, ts timestamptz);"
psql_p "INSERT INTO accounts SELECT i, 0 FROM generate_series(1, 1000) i ON CONFLICT DO NOTHING;"
psql_p "TRUNCATE audit;"
psql_p "CHECKPOINT;"
sleep 3  # let standby catch up

# Reset IO stats
reset_io_stats "$PRIMARY_PORT"
if [ "$MODE" = "cascade" ]; then
    reset_io_stats "$CASC1_PORT"
    reset_io_stats "$CASC2_PORT"
else
    reset_io_stats "$STANDBY_PORT"
fi

# ── Start LSN ────────────────────────────────────────────────────────────────
if [ "$MODE" = "cascade" ]; then
    START_LSN=$(psql_c2 "SELECT pg_last_wal_replay_lsn()")
else
    START_LSN=$(psql_s "SELECT pg_last_wal_replay_lsn()")
fi
START_TS=$(date +%s.%N)

# ── Background lag collector (every 2s) ──────────────────────────────────────
( while true; do
    psql -p "$PRIMARY_PORT" -d postgres -At -c \
      "SELECT clock_timestamp()||','||application_name||','||coalesce(flush_lag::text,'')||','||coalesce(replay_lag::text,'') FROM pg_stat_replication"
    >> "$OUT/lag.csv" 2>/dev/null
    sleep 2
done ) &
LAG_PID=$!

# ── pgbench run ──────────────────────────────────────────────────────────────
log "[$LABEL] Running pgbench: $CLIENTS clients, ${DURATION}s..."
pgbench -p "$PRIMARY_PORT" -d postgres --no-vacuum \
    -f "$SQL_DIR/walheavy.sql" \
    --client="$CLIENTS" --jobs=4 \
    --time="$DURATION" \
    > "$OUT/pgbench.log" 2>&1

# ── End ──────────────────────────────────────────────────────────────────────
END_TS=$(date +%s.%N)
if [ "$MODE" = "cascade" ]; then
    END_LSN=$(psql_c2 "SELECT pg_last_wal_replay_lsn()")
else
    END_LSN=$(psql_s "SELECT pg_last_wal_replay_lsn()")
fi

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
if [ "$MODE" = "cascade" ]; then
    for node_port in "casc1:$CASC1_PORT" "casc2:$CASC2_PORT"; do
        node="${node_port%%:*}"
        port="${node_port##*:}"
        psql -p "$port" -d postgres -c "
        SELECT backend_type, object, context,
               reads, writes, writebacks, fsyncs, extends,
               read_time, write_time, writeback_time, fsync_time
        FROM pg_stat_io
        WHERE backend_type IN ('walreceiver','walrcvflusher','startup','checkpointer')
          AND object = 'wal'
        ORDER BY backend_type, context;" > "$OUT/pg_stat_io_${node}.txt" 2>&1
    done
    FLUSHER_FSYNCS=$(psql_c1 "SELECT coalesce(sum(fsyncs),0) FROM pg_stat_io WHERE object='wal' AND backend_type='walrcvflusher'" 2>/dev/null)
    FLUSHER_FSYNC_TIME=$(psql_c1 "SELECT coalesce(sum(fsync_time),0) FROM pg_stat_io WHERE object='wal' AND backend_type='walrcvflusher'" 2>/dev/null)
    WALRCV_FSYNCS=$(psql_c1 "SELECT coalesce(sum(fsyncs),0) FROM pg_stat_io WHERE object='wal' AND backend_type='walreceiver'" 2>/dev/null)
    WALRCV_FSYNC_TIME=$(psql_c1 "SELECT coalesce(sum(fsync_time),0) FROM pg_stat_io WHERE object='wal' AND backend_type='walreceiver'" 2>/dev/null)
else
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
fi

# ── pg_stat_replication ──────────────────────────────────────────────────────
psql -p "$PRIMARY_PORT" -d postgres -c "
SELECT application_name, state, sync_state,
       sent_lsn, write_lsn, flush_lsn, replay_lsn,
       write_lag, flush_lag, replay_lag
FROM pg_stat_replication;" > "$OUT/pg_stat_replication.txt" 2>&1

# ── Summary ──────────────────────────────────────────────────────────────────
echo "label=$LABEL mode=$MODE throttle_ms=$THROTTLE_MS_VAL clients=$CLIENTS elapsed=${ELAPSED}s" \
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
echo "$LABEL,$VARIANT,$MODE,$THROTTLE_MS_VAL,$CLIENTS,$ELAPSED,$WAL_BPS,$WAL_DELTA,$FLUSHER_FSYNCS,$FLUSHER_FSYNC_TIME,$WALRCV_FSYNCS,$WALRCV_FSYNC_TIME" \
    >> "$RESULTS_DIR/walheavy_matrix.csv"

log "[$LABEL] Done: wal_recv_bps=$WAL_BPS ($WAL_DELTA_HR in ${ELAPSED}s)"
log "  flusher: $FLUSHER_FSYNCS fsyncs (${FLUSHER_FSYNC_TIME}ms)"
log "  walrcv:  $WALRCV_FSYNCS fsyncs (${WALRCV_FSYNC_TIME}ms)"
