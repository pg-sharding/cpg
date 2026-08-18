#!/bin/bash
# setup.sh — initialize primary + standby for benchmark scenarios S0-S6, S8-S11
# Usage:  ./setup.sh [throttle]
#   throttle  — start standby with LD_PRELOAD fsync throttle (uses THROTTLE_MS)
#
# THROTTLE_MS env var controls fsync delay:
#   THROTTLE_MS=0   — no throttle (fast flush, default)
#   THROTTLE_MS=1   — 1ms per fsync (fast flush simulation)
#   THROTTLE_MS=10  — 10ms per fsync
#   THROTTLE_MS=50  — 50ms per fsync (slow disk simulation)
#   THROTTLE_MS=100 — 100ms per fsync (very slow disk)
#
# When THROTTLE_MS=0 and "throttle" is passed, the .so is still loaded but
# fsync returns immediately (no delay). This tests the LD_PRELOAD overhead.

source "$(dirname "$0")/common.sh"

mkdir -p "$WORK_DIR" "$RESULTS_DIR"
stop_all
rm -rf "$PRIMARY_DATA" "$STANDBY_DATA"
mkdir -p "$PRIMARY_DATA" "$STANDBY_DATA"

# ── Primary ───────────────────────────────────────────────────────────────────
log "Initializing primary..."
initdb -D "$PRIMARY_DATA" --auth=trust --wal-segsize="$WAL_SEG_SIZE" 2>&1 | tail -1

cat >> "$PRIMARY_DATA/postgresql.conf" <<EOF
$(common_conf)
port = $PRIMARY_PORT
wal_keep_size = 4GB
wal_sender_timeout = 60s
synchronous_commit = off
synchronous_standby_names = ''
EOF

chmod 0700 "$PRIMARY_DATA"

pg_ctl -D "$PRIMARY_DATA" -l "$WORK_DIR/primary.log" start -w
log "Creating replication role and slot..."
psql_p "CREATE ROLE repl WITH REPLICATION LOGIN;" 2>/dev/null || true
psql_p "SELECT pg_create_physical_replication_slot('$SLOT_STANDBY');" 2>/dev/null || true

# ── Standby ──────────────────────────────────────────────────────────────────
log "Taking basebackup for standby..."
pg_basebackup -h localhost -p "$PRIMARY_PORT" -U repl \
    -D "$STANDBY_DATA" -X stream -S "$SLOT_STANDBY" -c fast --progress 2>&1 | tail -1

cat >> "$STANDBY_DATA/postgresql.conf" <<EOF
$(common_conf)
port = $STANDBY_PORT
hot_standby = on
hot_standby_feedback = on
wal_receiver_status_interval = 1s
wal_receiver_timeout = 60s
EOF

chmod 0700 "$STANDBY_DATA"

touch "$STANDBY_DATA/standby.signal"

cat > "$STANDBY_DATA/postgresql.auto.conf" <<EOF
primary_conninfo = 'host=localhost port=$PRIMARY_PORT user=repl application_name=standby1'
primary_slot_name = '$SLOT_STANDBY'
EOF

# ── Start standby (optionally with throttle) ─────────────────────────────────
if [ "${1:-}" = "throttle" ]; then
    start_node "$STANDBY_DATA" "$WORK_DIR/standby.log" throttle
else
    start_node "$STANDBY_DATA" "$WORK_DIR/standby.log"
fi

wait_for_streaming "$PRIMARY_PORT" "standby1"
log "Setup complete. Primary port=$PRIMARY_PORT, Standby port=$STANDBY_PORT"
