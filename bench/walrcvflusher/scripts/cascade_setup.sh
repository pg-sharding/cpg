#!/bin/bash
# cascade_setup.sh — initialize 3-node cascade: primary → replica1 → replica2
# Usage:  ./cascade_setup.sh [throttle]

source "$(dirname "$0")/common.sh"

mkdir -p "$WORK_DIR" "$RESULTS_DIR"
stop_all
rm -rf "$PRIMARY_DATA" "$STANDBY_DATA" "$CASC1_DATA" "$CASC2_DATA"
mkdir -p "$PRIMARY_DATA" "$CASC1_DATA" "$CASC2_DATA"

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

pg_ctl -D "$PRIMARY_DATA" -l "$WORK_DIR/primary.log" start -w
psql_p "CREATE ROLE repl WITH REPLICATION LOGIN;" 2>/dev/null || true
psql_p "SELECT pg_create_physical_replication_slot('$SLOT_CASC1');" 2>/dev/null || true

# ── Replica1 (samurai) — standby of primary, walsender for replica2 ────────────
log "Taking basebackup for cascade replica1..."
pg_basebackup -h localhost -p "$PRIMARY_PORT" -U repl \
    -D "$CASC1_DATA" -X stream -S "$SLOT_CASC1" -c fast --progress 2>&1 | tail -1

cat >> "$CASC1_DATA/postgresql.conf" <<EOF
$(common_conf)
port = $CASC1_PORT
hot_standby = on
hot_standby_feedback = on
wal_receiver_status_interval = 1s
wal_receiver_timeout = 60s
EOF

touch "$CASC1_DATA/standby.signal"
cat > "$CASC1_DATA/postgresql.auto.conf" <<EOF
primary_conninfo = 'host=localhost port=$PRIMARY_PORT user=repl application_name=casc1'
primary_slot_name = '$SLOT_CASC1'
EOF

# Start replica1 (optionally with throttle)
if [ "${1:-}" = "throttle" ]; then
    start_node "$CASC1_DATA" "$WORK_DIR/casc1.log" throttle
else
    start_node "$CASC1_DATA" "$WORK_DIR/casc1.log"
fi
wait_for_streaming "$PRIMARY_PORT" "casc1"

# Create slot for replica2 on replica1
psql_c1 "SELECT pg_create_physical_replication_slot('$SLOT_CASC2');" 2>/dev/null || true

# ── Replica2 (stubble) — standby of replica1 ──────────────────────────────────
log "Taking basebackup for cascade replica2..."
pg_basebackup -h localhost -p "$CASC1_PORT" -U repl \
    -D "$CASC2_DATA" -X stream -S "$SLOT_CASC2" -c fast --progress 2>&1 | tail -1

cat >> "$CASC2_DATA/postgresql.conf" <<EOF
$(common_conf)
port = $CASC2_PORT
hot_standby = on
hot_standby_feedback = on
wal_receiver_status_interval = 1s
wal_receiver_timeout = 60s
EOF

touch "$CASC2_DATA/standby.signal"
cat > "$CASC2_DATA/postgresql.auto.conf" <<EOF
primary_conninfo = 'host=localhost port=$CASC1_PORT user=repl application_name=casc2'
primary_slot_name = '$SLOT_CASC2'
EOF

start_node "$CASC2_DATA" "$WORK_DIR/casc2.log"
wait_for_streaming "$CASC1_PORT" "casc2"

log "Cascade setup complete: primary:$PRIMARY_PORT → casc1:$CASC1_PORT → casc2:$CASC2_PORT"
