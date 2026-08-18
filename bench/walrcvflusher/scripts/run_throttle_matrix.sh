#!/bin/bash
# run_throttle_matrix.sh — run benchmarks at multiple throttle levels
#
# Usage:  ./run_throttle_matrix.sh <variant> [throttle_levels]
#
#   variant         — "baseline" or "new"
#   throttle_levels — space-separated list of THROTTLE_MS values
#                      default: "0 1 10 50 100"
#
# For each throttle level:
#   1. setup.sh throttle (or plain if 0)
#   2. Run S0 (TPC-B, 32 clients, 30s)
#   3. Collect pg_stat_io, pg_stat_replication, summary
#
# Results saved to results/<variant>_throttle<throttle_ms>/
#
# Example:
#   ./run_throttle_matrix.sh new "0 1 10 50"
#   ./run_throttle_matrix.sh baseline "0 50"

source "$(dirname "$0")/common.sh"

VARIANT="${1:?Usage: run_throttle_matrix.sh <baseline|new> [throttle_levels]}"
THROTTLE_LEVELS="${2:-0 1 10 50 100}"

# Results CSV header
echo "label,throttle_ms,wal_recv_bps,wal_delta_bytes,elapsed_sec,tpps,flush_lag_ms,replay_lag_ms,flusher_fsyncs,flusher_fsync_time_ms,walrcv_fsyncs,walrcv_fsync_time_ms" > "$RESULTS_DIR/throttle_matrix.csv"

for THROTTLE_MS in $THROTTLE_LEVELS; do
    LABEL="${VARIANT}_throttle${THROTTLE_MS}"
    OUT="$RESULTS_DIR/$LABEL"
    mkdir -p "$OUT"

    log "=== $LABEL: THROTTLE_MS=$THROTTLE_MS ==="

    # Setup
    if [ "$THROTTLE_MS" -eq 0 ]; then
        ./scripts/setup.sh 2>&1 | tail -2
    else
        ./scripts/setup.sh throttle 2>&1 | tail -2
    fi

    # Init pgbench tables
    pgbench -i -p "$PRIMARY_PORT" -d postgres >/dev/null 2>&1
    sleep 5  # let standby catch up

    # Reset IO stats
    reset_io_stats "$PRIMARY_PORT"
    reset_io_stats "$STANDBY_PORT"

    # Start LSN
    START_LSN=$(psql -p "$STANDBY_PORT" -d postgres -At -c "SELECT pg_last_wal_replay_lsn()")
    START_TS=$(date +%s.%N)

    # Background lag collector (every 2s)
    ( while true; do
        psql -p "$PRIMARY_PORT" -d postgres -At -c \
          "SELECT clock_timestamp()||','||application_name||','||sent_lsn||','||write_lsn||','||flush_lsn||','||replay_lsn||','||coalesce(write_lag::text,'')||','||coalesce(flush_lag::text,'')||','||coalesce(replay_lag::text,'') FROM pg_stat_replication"
        >> "$OUT/lag.csv" 2>/dev/null
        sleep 2
      done ) &
    LAG_PID=$!

    # Run pgbench
    log "[$LABEL] Running pgbench for ${DURATION}s..."
    pgbench -p "$PRIMARY_PORT" -d postgres --no-vacuum --time="$DURATION" \
        --client=32 --jobs=8 > "$OUT/pgbench.log" 2>&1

    # End LSN
    END_TS=$(date +%s.%N)
    END_LSN=$(psql -p "$STANDBY_PORT" -d postgres -At -c "SELECT pg_last_wal_replay_lsn()")

    # Stop lag collector
    kill $LAG_PID 2>/dev/null; wait 2>/dev/null

    # Compute metrics
    ELAPSED=$(echo "$END_TS - $START_TS" | bc -l)
    WAL_DELTA=$(psql -p "$STANDBY_PORT" -d postgres -At -c "SELECT pg_wal_lsn_diff('$END_LSN','$START_LSN')::bigint")
    WAL_BPS=$(echo "scale=0; $WAL_DELTA / $ELAPSED" | bc -l)
    TPS=$(grep "tps =" "$OUT/pgbench.log" | head -1 | sed 's/.*tps = //' | sed 's/ .*//')

    # pg_stat_io snapshot
    psql -p "$STANDBY_PORT" -d postgres -c "
    SELECT backend_type, object, context,
           reads, writes, writebacks, fsyncs, extends,
           read_time, write_time, writeback_time, fsync_time
    FROM pg_stat_io
    WHERE backend_type IN ('walreceiver','walrcvflusher','startup','checkpointer')
      AND object = 'wal'
    ORDER BY backend_type, context;" > "$OUT/pg_stat_io.txt" 2>&1

    # fsync timing summary
    psql -p "$STANDBY_PORT" -d postgres -c "
    SELECT backend_type, fsyncs,
           round(fsync_time::numeric / greatest(fsyncs,1), 3) AS avg_fsync_ms,
           fsync_time AS total_fsync_ms
    FROM pg_stat_io
    WHERE object = 'wal'
      AND backend_type IN ('walreceiver','walrcvflusher')
    ORDER BY backend_type;" > "$OUT/fsync_timing.txt" 2>&1

    # pg_stat_replication final
    psql -p "$PRIMARY_PORT" -d postgres -c "
    SELECT application_name, state, sync_state,
           sent_lsn, write_lsn, flush_lsn, replay_lsn,
           write_lag, flush_lag, replay_lag
    FROM pg_stat_replication;" > "$OUT/pg_stat_replication.txt" 2>&1

    # Extract final lag values (last row from lag.csv)
    LAST_LAG=$(tail -1 "$OUT/lag.csv" 2>/dev/null)
    FLUSH_LAG=$(echo "$LAST_LAG" | cut -d',' -f8 | sed 's/00:00://g' | sed 's/\.//g' | awk '{printf "%.3f", $1}')
    REPLAY_LAG=$(echo "$LAST_LAG" | cut -d',' -f9 | sed 's/00:00://g' | sed 's/\.//g' | awk '{printf "%.3f", $1}')

    # Extract fsync counts
    FLUSHER_FSYNCS=$(psql -p "$STANDBY_PORT" -d postgres -At -c "
        SELECT coalesce(sum(fsyncs),0) FROM pg_stat_io
        WHERE object='wal' AND backend_type='walrcvflusher'" 2>/dev/null)
    FLUSHER_FSYNC_TIME=$(psql -p "$STANDBY_PORT" -d postgres -At -c "
        SELECT coalesce(sum(fsync_time),0) FROM pg_stat_io
        WHERE object='wal' AND backend_type='walrcvflusher'" 2>/dev/null)
    WALRCV_FSYNCS=$(psql -p "$STANDBY_PORT" -d postgres -At -c "
        SELECT coalesce(sum(fsyncs),0) FROM pg_stat_io
        WHERE object='wal' AND backend_type='walreceiver'" 2>/dev/null)
    WALRCV_FSYNC_TIME=$(psql -p "$STANDBY_PORT" -d postgres -At -c "
        SELECT coalesce(sum(fsync_time),0) FROM pg_stat_io
        WHERE object='wal' AND backend_type='walreceiver'" 2>/dev/null)

    # Summary
    echo "label=$LABEL throttle_ms=$THROTTLE_MS elapsed=${ELAPSED}s wal_delta=${WAL_DELTA} wal_recv_bps=$WAL_BPS tps=$TPS flush_lag=${FLUSH_LAG}s replay_lag=${REPLAY_LAG}s" \
        | tee "$OUT/summary.txt"

    echo "$LABEL,$THROTTLE_MS,$WAL_BPS,$WAL_DELTA,$ELAPSED,$TPS,$FLUSH_LAG,$REPLAY_LAG,$FLUSHER_FSYNCS,$FLUSHER_FSYNC_TIME,$WALRCV_FSYNCS,$WALRCV_FSYNC_TIME" \
        >> "$RESULTS_DIR/throttle_matrix.csv"

    log "[$LABEL] Done: wal_recv_bps=$WAL_BPS tps=$TPS flush_lag=${FLUSH_LAG}s replay_lag=${REPLAY_LAG}s"
done

log "============================================"
log "Throttle matrix complete for variant: $VARIANT"
log "Results CSV: $RESULTS_DIR/throttle_matrix.csv"
log "Per-run details: $RESULTS_DIR/${VARIANT}_throttle*/"
log "============================================"
