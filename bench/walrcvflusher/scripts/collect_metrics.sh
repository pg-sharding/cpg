#!/bin/bash
# collect_metrics.sh — standalone metric collection (run separately from bench)
# Usage:  ./collect_metrics.sh <label> <duration_sec>
# Collects pg_stat_io, wait events, lag, and fsync timing from standby

source "$(dirname "$0")/common.sh"

LABEL="${1:?Usage: collect_metrics.sh <label> <duration_sec>}"
DURATION="${2:-60}"
OUT="$RESULTS_DIR/${LABEL}"
mkdir -p "$OUT"

log "Collecting metrics for ${DURATION}s..."

# ── pg_stat_io (full snapshot) ────────────────────────────────────────────────
psql -p "$STANDBY_PORT" -d postgres -c "
SELECT backend_type, object, context,
       reads, writes, writebacks, fsyncs, extends,
       op_bytes, read_bytes, write_bytes, writeback_bytes,
       reads_time, writes_time, writebacks_time, fsyncs_time,
       stats_reset
FROM pg_stat_io
ORDER BY backend_type, object, context;" > "$OUT/pg_stat_io_full.txt" 2>&1

# ── Wait events over duration ─────────────────────────────────────────────────
log "Sampling wait events for ${DURATION}s..."
( for i in $(seq 1 $((DURATION / 2))); do
    psql -p "$STANDBY_PORT" -d postgres -At -c "
      SELECT clock_timestamp()||','||pid||','||backend_type||','||
             coalesce(wait_event_type,'')||','||coalesce(wait_event,'')
      FROM pg_stat_activity
      WHERE backend_type IN ('walreceiver','walrcvflusher','startup')"
    sleep 2
  done ) > "$OUT/wait_events_timeseries.csv" 2>/dev/null

# ── Wait event summary ────────────────────────────────────────────────────────
psql -p "$STANDBY_PORT" -d postgres -c "
SELECT backend_type, wait_event_type, wait_event, count(*)
FROM pg_stat_activity
WHERE backend_type IN ('walreceiver','walrcvflusher','startup')
GROUP BY 1,2,3 ORDER BY 1,4 DESC;" > "$OUT/wait_events_summary.txt" 2>&1

# ── fsync timing per backend type ─────────────────────────────────────────────
psql -p "$STANDBY_PORT" -d postgres -c "
SELECT backend_type,
       fsyncs,
       round(fsyncs_time::numeric / greatest(fsyncs,1), 3) AS avg_fsync_ms,
       fsyncs_time AS total_fsync_ms,
       writes,
       round(writes_time::numeric / greatest(writes,1), 3) AS avg_write_ms
FROM pg_stat_io
WHERE object = 'wal'
  AND backend_type IN ('walreceiver','walrcvflusher','walsender')
ORDER BY backend_type;" > "$OUT/fsync_timing.txt" 2>&1

# ── Lag snapshot ──────────────────────────────────────────────────────────────
psql -p "$PRIMARY_PORT" -d postgres -c "
SELECT application_name, state, sync_state,
       sent_lsn, write_lsn, flush_lsn, replay_lsn,
       write_lag, flush_lag, replay_lag,
       pg_current_wal_lsn() AS current_lsn
FROM pg_stat_replication;" > "$OUT/pg_stat_replication.txt" 2>&1

# ── WAL receiver status ───────────────────────────────────────────────────────
psql_s "SELECT status, receive_start_lsn, receive_start_tli,
        written_lsn, flushed_lsn, received_lsn,
        latest_end_lsn, latest_end_time,
        conninfo
FROM pg_stat_wal_receiver;" > "$OUT/wal_receiver.txt" 2>&1

# ── pg_test_fsync characterization ────────────────────────────────────────────
if command -v pg_test_fsync &>/dev/null; then
    log "Running pg_test_fsync (5s per test)..."
    pg_test_fsync --secs-per-test=5 > "$OUT/pg_test_fsync.txt" 2>&1
fi

# ── pgbench log (if exists) ────────────────────────────────────────────────────
if [ -f "$OUT/pgbench.log" ]; then
    TPS=$(grep "tps =" "$OUT/pgbench.log" 2>/dev/null | head -1 || true)
    log "pgbench result: $TPS"
fi

log "Metrics collected in $OUT/"
