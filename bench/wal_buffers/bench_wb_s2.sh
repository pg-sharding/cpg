#!/bin/bash
# bench_wb_s2.sh — S2 benchmark with fsync throttle
# Usage: THROTTLE_MS=20 ./bench_wb_s2.sh <variant> <label>
set -euo pipefail

VARIANT="${1:?Usage: bench_wb_s2.sh <baseline|mine> <label>}"
LABEL="${2:?need label}"
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
OUT="$RESULTS/${LABEL}"
mkdir -p "$WORK" "$RESULTS" "$OUT"
THROTTLE_SO="$HOME/bench_wb/lib/fsync_throttle.so"
TMS="${THROTTLE_MS:-0}"

# Kill only my procs
pkill -9 -f "bench_wb/$VARIANT" 2>/dev/null || true
sleep 2

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

# Init primary (no throttle)
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

# Start standby — with throttle if TMS>0
if [ "$TMS" -gt 0 ] && [ -f "$THROTTLE_SO" ]; then
    echo "Starting standby with THROTTLE_MS=$TMS"
    LD_PRELOAD="$THROTTLE_SO" THROTTLE_MS="$TMS" \
        postgres -D "$S_DATA" >> "$WORK/standby.log" 2>&1 &
else
    pg_ctl -D "$S_DATA" -l "$WORK/standby.log" start -w
fi

# Wait for streaming (up to 5 min — throttle slows init)
for i in $(seq 1 300); do
    st=$(psql -p $P_PORT -d postgres -At -c "SELECT state FROM pg_stat_replication WHERE application_name='standby1'" 2>/dev/null || true)
    [ "$st" = "streaming" ] && break
    sleep 1
done
[ "$st" = "streaming" ] || { echo "FAIL: standby not streaming"; pkill -9 -f "bench_wb/$VARIANT" 2>/dev/null; exit 1; }
echo "Setup OK (throttle=${TMS}ms): primary=$P_PORT standby=$S_PORT"

# pgbench init + warmup (on primary, not affected by throttle)
pgbench -p $P_PORT -d postgres -i >/dev/null 2>&1 || true
echo "[$LABEL] Warmup 10s..."
pgbench -p $P_PORT -d postgres --no-vacuum --time=10 --builtin=tpcb --client=16 --jobs=4 >/dev/null 2>&1 || true

# Reset stats
psql -p $P_PORT -d postgres -c "SELECT pg_stat_reset_shared('io');" >/dev/null 2>&1 || true
psql -p $S_PORT -d postgres -c "SELECT pg_stat_reset_shared('io');" >/dev/null 2>&1 || true

# Start positions
START_RECV=$(timeout 5 psql -p $S_PORT -d postgres -At -c "SELECT pg_last_wal_receive_lsn()" 2>/dev/null || echo "0/0")
START_TS=$(date +%s.%N)

# Background lag collector (from primary, not throttled)
( while true; do
    psql -p $P_PORT -d postgres -At -c \
      "SELECT clock_timestamp()||','||application_name||','||sent_lsn||','||write_lsn||','||flush_lsn||','||replay_lsn||','||coalesce(write_lag::text,'')||','||coalesce(flush_lag::text,'')||','||coalesce(replay_lag::text,'') FROM pg_stat_replication" \
      >> "$OUT/lag.csv" 2>/dev/null || true
    sleep 2
  done ) &
LAG_PID=$!

# pgbench run
DURATION=60
echo "[$LABEL] Running pgbench for ${DURATION}s (throttle=${TMS}ms)..."
pgbench -p $P_PORT -d postgres --no-vacuum --time=$DURATION --builtin=tpcb --client=32 --jobs=8 \
    > "$OUT/pgbench.log" 2>&1

# End positions (query primary for sent/write; standby may be slow under throttle)
END_TS=$(date +%s.%N)
END_RECV=$(timeout 5 psql -p $S_PORT -d postgres -At -c "SELECT pg_last_wal_receive_lsn()" 2>/dev/null || echo "$START_RECV")

# Stop lag collector
kill $LAG_PID 2>/dev/null || true
sleep 1

# Compute results (use primary for lsn_diff — standby may be slow under throttle)
ELAPSED=$(echo "$END_TS - $START_TS" | bc -l)
WAL_DELTA=$(psql -p $P_PORT -d postgres -At -c "SELECT pg_wal_lsn_diff('$END_RECV','$START_RECV')::bigint" 2>/dev/null || echo "0")
WAL_BPS=$(echo "scale=0; $WAL_DELTA / $ELAPSED" | bc -l)
WAL_MBPS=$(echo "scale=2; $WAL_BPS / 1048576" | bc -l)
WAL_DELTA_HR=$(psql -p $P_PORT -d postgres -At -c "SELECT pg_size_pretty($WAL_DELTA::bigint)" 2>/dev/null || echo "?")

TPS=$(grep "tps =" "$OUT/pgbench.log" 2>/dev/null | head -1 || true)
LAST_LAG=$(tail -1 "$OUT/lag.csv" 2>/dev/null || true)

echo "label=$LABEL throttle=${TMS}ms elapsed=${ELAPSED}s wal_delta=$WAL_DELTA_HR wal_recv_bps=$WAL_BPS wal_recv_mbps=$WAL_MBPS" | tee "$OUT/summary.txt"
echo "pgbench: $TPS" >> "$OUT/summary.txt"
echo "last_lag: $LAST_LAG" >> "$OUT/summary.txt"

# pg_stat_io (best effort, may timeout under throttle)
timeout 10 psql -p $S_PORT -d postgres -c "
SELECT backend_type, writes, fsyncs,
       round(write_time::numeric / greatest(writes,1), 3) AS avg_write_ms,
       round(fsync_time::numeric / greatest(fsyncs,1), 3) AS avg_fsync_ms
FROM pg_stat_io
WHERE object = 'wal'
  AND backend_type IN ('walreceiver','walrcvflusher')
ORDER BY backend_type;" > "$OUT/pg_stat_io.txt" 2>&1 || echo "timeout" > "$OUT/pg_stat_io.txt"

echo "[$LABEL] Done: wal_recv_mbps=$WAL_MBPS ($WAL_DELTA_HR in ${ELAPSED}s)"
echo "$LABEL,$TMS,$WAL_BPS,$WAL_MBPS,$WAL_DELTA,$ELAPSED" >> "$RESULTS/ALL_S2.csv"

# Shutdown: kill standby first (fast), then primary
pkill -9 -f "bench_wb/$VARIANT.*standby" 2>/dev/null || true
sleep 1
pg_ctl -D "$P_DATA" stop -m fast -w 2>/dev/null || true
pkill -9 -f "bench_wb/$VARIANT" 2>/dev/null || true
