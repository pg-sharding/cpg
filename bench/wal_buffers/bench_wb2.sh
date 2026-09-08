#!/bin/bash
# bench_wb2.sh — benchmark wal buffers (mine) vs baseline (flusher only)
# Usage: ./bench_wb2.sh <variant> <label> [pgbench_args...]
#   variant = "baseline" | "mine"
#   Special labels: S0=tpcb, S3=smalltx, S9=walheavy
set -euo pipefail

VARIANT="${1:?Usage: bench_wb2.sh <baseline|mine> <label> [pgbench_args...]}"
LABEL="${2:?need label}"
shift 2
EXTRA_ARGS=("$@")

PGINST="$HOME/bench_wb/$VARIANT/pginst"
export PATH="$PGINST/bin:$PATH"
export LANG=C LC_ALL=C
export PGHOST=localhost

P_PORT=55532
S_PORT=55533

WORK="$HOME/bench_wb/$VARIANT/work"
P_DATA="$WORK/primary"
S_DATA="$WORK/standby"
RESULTS="$HOME/bench_wb/results"
mkdir -p "$WORK" "$RESULTS"
OUT="$RESULTS/${LABEL}"
mkdir -p "$OUT"

# Stop only my clusters
pg_ctl -D "$S_DATA" stop -m fast -w 2>/dev/null || true
pg_ctl -D "$P_DATA" stop -m fast -w 2>/dev/null || true
sleep 1
rm -rf "$P_DATA" "$S_DATA"
mkdir -p "$P_DATA" "$S_DATA"

COMMON="
listen_addresses = 'localhost'
shared_buffers = 1GB
max_wal_size = 16GB
min_wal_size = 1GB
checkpoint_timeout = 1h
autovacuum = off
track_io_timing = on
track_wal_io_timing = on
logging_collector = on
log_min_messages = warning
wal_level = replica
max_wal_senders = 10
max_replication_slots = 10
wal_sender_timeout = 60s
synchronous_commit = off
synchronous_standby_names = ''
"

# Init primary
initdb -D "$P_DATA" --auth=trust --wal-segsize=16 >/dev/null 2>&1
chmod 0700 "$P_DATA"
cat >> "$P_DATA/postgresql.conf" <<EOF
$COMMON
port = $P_PORT
wal_keep_size = 4GB
EOF
pg_ctl -D "$P_DATA" -l "$WORK/primary.log" start -w
sleep 1
psql -p $P_PORT -d postgres -At -c "CREATE ROLE repl WITH REPLICATION LOGIN;" 2>/dev/null || true
psql -p $P_PORT -d postgres -At -c "SELECT pg_create_physical_replication_slot('sb_slot');" 2>/dev/null || true

# Init standby
pg_basebackup -h localhost -p $P_PORT -U repl -D "$S_DATA" -X stream -S sb_slot -c fast --progress >/dev/null 2>&1
chmod 0700 "$S_DATA"
cat >> "$S_DATA/postgresql.conf" <<EOF
$COMMON
port = $S_PORT
hot_standby = on
hot_standby_feedback = on
wal_receiver_status_interval = 1s
EOF
touch "$S_DATA/standby.signal"
cat > "$S_DATA/postgresql.auto.conf" <<EOF
primary_conninfo = 'host=localhost port=$P_PORT user=repl application_name=standby1'
primary_slot_name = 'sb_slot'
EOF

# Start standby — with throttle if THROTTLE_MS>0 (pg_ctl clears LD_PRELOAD)
THROTTLE_SO="$HOME/bench_wb/lib/fsync_throttle.so"
if [ "${THROTTLE_MS:-0}" -gt 0 ] && [ -f "$THROTTLE_SO" ]; then
    echo "Starting standby with THROTTLE_MS=${THROTTLE_MS} (LD_PRELOAD)"
    LD_PRELOAD="$THROTTLE_SO" THROTTLE_MS="$THROTTLE_MS" \
        postgres -D "$S_DATA" -c logging_collector=on \
        >> "$WORK/standby.log" 2>&1 &
    # Wait for postmaster.pid
    for i in $(seq 1 60); do
        [ -f "$S_DATA/postmaster.pid" ] && break
        sleep 1
    done
else
    pg_ctl -D "$S_DATA" -l "$WORK/standby.log" start -w
fi

# Wait for streaming
for i in $(seq 1 60); do
    st=$(psql -p $P_PORT -d postgres -At -c "SELECT state FROM pg_stat_replication WHERE application_name='standby1'" 2>/dev/null || true)
    [ "$st" = "streaming" ] && break
    sleep 1
done
[ "$st" = "streaming" ] || { echo "FAIL: standby not streaming"; exit 1; }
echo "Setup OK: primary=$P_PORT standby=$S_PORT"

# Prepare tables for custom scripts
SQLDIR="$HOME/work/cpg/bench/walrcvflusher/sql"
psql -p $P_PORT -d postgres -f "$SQLDIR/prepare_tables.sql" >/dev/null 2>&1 || true
sleep 1  # let WAL propagate

# Determine pgbench args by label
DURATION=60
WARMUP=15
case "$LABEL" in
  *S0*)
    BENCH_ARGS=(--builtin=tpcb --client=32 --jobs=8)
    INIT=yes
    ;;
  *S3*)
    BENCH_ARGS=(-f "$SQLDIR/smalltx.sql" --client=64 --no-vacuum)
    INIT=no
    ;;
  *S9*)
    BENCH_ARGS=(-f "$SQLDIR/walheavy.sql" --client=32 --no-vacuum)
    INIT=no
    ;;
  *)
    BENCH_ARGS=("${EXTRA_ARGS[@]}")
    INIT=no
    ;;
esac

# Warmup
echo "[$LABEL] Warmup ${WARMUP}s..."
if [ "$INIT" = "yes" ]; then
    pgbench -p $P_PORT -d postgres -i >/dev/null 2>&1 || true
fi
pgbench -p $P_PORT -d postgres --no-vacuum --time=$WARMUP --client=16 --jobs=4 >/dev/null 2>&1 || true

# Reset stats
psql -p $P_PORT -d postgres -c "SELECT pg_stat_reset_shared('io');" >/dev/null 2>&1 || true
psql -p $S_PORT -d postgres -c "SELECT pg_stat_reset_shared('io');" >/dev/null 2>&1 || true

# Start positions
START_RECV=$(psql -p $S_PORT -d postgres -At -c "SELECT pg_last_wal_receive_lsn()")
START_TS=$(date +%s.%N)

# Background lag collector
( while true; do
    psql -p $P_PORT -d postgres -At -c \
      "SELECT clock_timestamp()||','||application_name||','||sent_lsn||','||write_lsn||','||flush_lsn||','||replay_lsn||','||coalesce(write_lag::text,'')||','||coalesce(flush_lag::text,'')||','||coalesce(replay_lag::text,'') FROM pg_stat_replication" \
      >> "$OUT/lag.csv" 2>/dev/null || true
    sleep 2
  done ) &
LAG_PID=$!

# Background wal_receiver collector
( while true; do
    psql -p $S_PORT -d postgres -At -c \
      "SELECT clock_timestamp()||','||written_lsn||','||flushed_lsn||','||latest_end_lsn" \
      >> "$OUT/walrcv.csv" 2>/dev/null || true
    sleep 2
  done ) &
WRCV_PID=$!

# pgbench run
echo "[$LABEL] Running pgbench for ${DURATION}s..."
pgbench -p $P_PORT -d postgres --no-vacuum --time=$DURATION "${BENCH_ARGS[@]}" \
    > "$OUT/pgbench.log" 2>&1

# End positions
END_TS=$(date +%s.%N)
END_RECV=$(psql -p $S_PORT -d postgres -At -c "SELECT pg_last_wal_receive_lsn()")

# Stop collectors
kill $LAG_PID $WRCV_PID 2>/dev/null || true
wait 2>/dev/null || true

# Compute WAL receive rate
ELAPSED=$(echo "$END_TS - $START_TS" | bc -l)
WAL_DELTA=$(psql -p $S_PORT -d postgres -At -c "SELECT pg_wal_lsn_diff('$END_RECV','$START_RECV')::bigint")
WAL_BPS=$(echo "scale=0; $WAL_DELTA / $ELAPSED" | bc -l)
WAL_MBPS=$(echo "scale=2; $WAL_BPS / 1048576" | bc -l)
WAL_DELTA_HR=$(psql -p $S_PORT -d postgres -At -c "SELECT pg_size_pretty($WAL_DELTA::bigint)")

echo "label=$LABEL elapsed=${ELAPSED}s wal_delta=$WAL_DELTA_HR wal_recv_bps=$WAL_BPS wal_recv_mbps=$WAL_MBPS" | tee "$OUT/summary.txt"

# pgbench tps
TPS=$(grep "tps =" "$OUT/pgbench.log" 2>/dev/null | head -1 || true)
echo "pgbench: $TPS" >> "$OUT/summary.txt"

# pg_stat_io snapshot
psql -p $S_PORT -d postgres -c "
SELECT backend_type, object, context,
       reads, writes, writebacks, fsyncs, extends,
       read_time, write_time, writeback_time, fsync_time
FROM pg_stat_io
WHERE backend_type IN ('walreceiver','walrcvflusher','startup','checkpointer','bgwriter')
  AND object = 'wal'
ORDER BY backend_type, context;" > "$OUT/pg_stat_io.txt" 2>&1

# pg_stat_replication final
psql -p $P_PORT -d postgres -c "
SELECT application_name, state, sync_state,
       sent_lsn, write_lsn, flush_lsn, replay_lsn,
       write_lag, flush_lag, replay_lag
FROM pg_stat_replication;" > "$OUT/pg_stat_replication.txt" 2>&1

# Last lag line (final replay_lag)
LAST_LAG=$(tail -1 "$OUT/lag.csv" 2>/dev/null || true)
echo "last_lag: $LAST_LAG" >> "$OUT/summary.txt"

echo "[$LABEL] Done: wal_recv_bps=$WAL_BPS wal_recv_mbps=$WAL_MBPS ($WAL_DELTA_HR in ${ELAPSED}s)"
echo "$LABEL,$WAL_BPS,$WAL_MBPS,$WAL_DELTA,$ELAPSED" >> "$RESULTS/ALL2.csv"

# Stop cluster
pg_ctl -D "$S_DATA" stop -m fast -w 2>/dev/null || true
pg_ctl -D "$P_DATA" stop -m fast -w 2>/dev/null || true
