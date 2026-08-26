#!/bin/bash
# run_bench.sh — run a single benchmark scenario, collect metrics
# Usage:  ./run_bench.sh <label> <pgbench_args...>
# Example: ./run_bench.sh S0_tpcb --builtin=tpcb --client=32 --jobs=8

source "$(dirname "$0")/common.sh"

LABEL="${1:?Usage: run_bench.sh <label> <pgbench_args...>}"
shift

OUT="$RESULTS_DIR/${LABEL}"
mkdir -p "$OUT"

# ── Warmup ────────────────────────────────────────────────────────────────────
log "[$LABEL] Warmup ${WARMUP}s..."
pgbench -p "$PRIMARY_PORT" -d postgres -i >/dev/null 2>&1 || true
pgbench -p "$PRIMARY_PORT" -d postgres --no-vacuum --time="$WARMUP" \
    --client=16 --jobs=4 >/dev/null 2>&1 || true

# ── Reset stats ──────────────────────────────────────────────────────────────
reset_io_stats "$PRIMARY_PORT"
reset_io_stats "$STANDBY_PORT"
psql_p "SELECT pg_stat_statements_reset();" >/dev/null 2>&1 || true

# ── Start positions ──────────────────────────────────────────────────────────
START_RECV=$(psql_s "SELECT pg_last_wal_receive_lsn()")
START_TS=$(date +%s.%N)

# ── Background lag collector (every 2s) ──────────────────────────────────────
( while true; do
    psql -p "$PRIMARY_PORT" -d postgres -At -c \
      "SELECT clock_timestamp()||','||application_name||','||sent_lsn||','||write_lsn||','||flush_lsn||','||replay_lsn||','||coalesce(write_lag::text,'')||','||coalesce(flush_lag::text,'')||','||coalesce(replay_lag::text,'') FROM pg_stat_replication"
    >> "$OUT/lag.csv" 2>/dev/null
    sleep 2
  done ) &
LAG_PID=$!

# ── Background wal_receiver collector (every 2s) ────────────────────────────
( while true; do
    psql_s "SELECT clock_timestamp()||','||written_lsn||','||flushed_lsn||','||latest_end_lsn" \
      >> "$OUT/walrcv.csv" 2>/dev/null
    sleep 2
  done ) &
WRCV_PID=$!

# ── iostat background ────────────────────────────────────────────────────────
iostat -x 2 $((DURATION / 2 + 5)) > "$OUT/iostat.txt" 2>/dev/null &
IOSTAT_PID=$!

# ── pgbench run ──────────────────────────────────────────────────────────────
log "[$LABEL] Running pgbench for ${DURATION}s..."
pgbench -p "$PRIMARY_PORT" -d postgres --no-vacuum --time="$DURATION" "$@" \
    > "$OUT/pgbench.log" 2>&1

# ── End positions ────────────────────────────────────────────────────────────
END_TS=$(date +%s.%N)
END_RECV=$(psql_s "SELECT pg_last_wal_receive_lsn()")

# ── Stop background collectors ────────────────────────────────────────────────
kill $LAG_PID $WRCV_PID $IOSTAT_PID 2>/dev/null; wait 2>/dev/null

# ── Compute WAL receive rate ──────────────────────────────────────────────────
ELAPSED=$(echo "$END_TS - $START_TS" | bc -l)
WAL_DELTA=$(psql_s "SELECT pg_wal_lsn_diff('$END_RECV','$START_RECV')::bigint")
WAL_BPS=$(echo "scale=0; $WAL_DELTA / $ELAPSED" | bc -l)
WAL_DELTA_HR=$(psql_s "SELECT pg_size_pretty($WAL_DELTA::bigint)")

echo "label=$LABEL elapsed=${ELAPSED}s wal_delta=$WAL_DELTA_HR wal_recv_bps=$WAL_BPS" \
    | tee "$OUT/summary.txt"

# ── pg_stat_io snapshot ───────────────────────────────────────────────────────
psql -p "$STANDBY_PORT" -d postgres -c "
SELECT backend_type, object, context,
       reads, writes, writebacks, fsyncs, extends,
       read_time, write_time, writeback_time, fsync_time
FROM pg_stat_io
WHERE backend_type IN ('walreceiver','walrcvflusher','startup','checkpointer','bgwriter')
  AND object = 'wal'
ORDER BY backend_type, context;" > "$OUT/pg_stat_io.txt" 2>&1

# ── Wait events snapshot ──────────────────────────────────────────────────────
psql -p "$STANDBY_PORT" -d postgres -c "
SELECT pid, backend_type, wait_event_type, wait_event, state
FROM pg_stat_activity
WHERE backend_type IN ('walreceiver','walrcvflusher','startup')
ORDER BY backend_type;" > "$OUT/wait_events.txt" 2>&1

# ── fsync timing summary (if track_wal_io_timing) ─────────────────────────────
psql -p "$STANDBY_PORT" -d postgres -c "
SELECT backend_type,
       fsyncs,
       round(fsync_time::numeric / greatest(fsyncs,1), 3) AS avg_fsync_ms,
       fsync_time AS total_fsync_ms
FROM pg_stat_io
WHERE object = 'wal'
  AND backend_type IN ('walreceiver','walrcvflusher')
ORDER BY backend_type;" > "$OUT/fsync_timing.txt" 2>&1

# ── pg_stat_replication final ────────────────────────────────────────────────
psql -p "$PRIMARY_PORT" -d postgres -c "
SELECT application_name, state, sync_state,
       sent_lsn, write_lsn, flush_lsn, replay_lsn,
       write_lag, flush_lag, replay_lag
FROM pg_stat_replication;" > "$OUT/pg_stat_replication.txt" 2>&1

# ── pgbench tps extraction ───────────────────────────────────────────────────
TPS=$(grep "tps =" "$OUT/pgbench.log" 2>/dev/null | head -1 || true)
echo "pgbench: $TPS" >> "$OUT/summary.txt"

log "[$LABEL] Done: wal_recv_bps=$WAL_BPS ($WAL_DELTA_HR in ${ELAPSED}s)"
echo "$LABEL,$WAL_BPS,$WAL_DELTA,$ELAPSED" >> "$RESULTS_DIR/ALL.csv"
