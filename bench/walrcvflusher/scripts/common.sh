#!/bin/bash
# common.sh — shared configuration and helper functions for walrcvflusher benchmarks
# Source this from other scripts: source "$(dirname "$0")/common.sh"

set -euo pipefail

# ── Paths ────────────────────────────────────────────────────────────────────
BENCH_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SCRIPTS_DIR="$BENCH_ROOT/scripts"
SQL_DIR="$BENCH_ROOT/sql"
RESULTS_DIR="$BENCH_ROOT/results"

# PostgreSQL install prefix — adjust to your build
PGINST="${PGINST:-$(pwd)/pginst}"
export PATH="$PGINST/bin:$PATH"
export PGHOST=localhost

# ── Topology ports ───────────────────────────────────────────────────────────
export PRIMARY_PORT="${PRIMARY_PORT:-55432}"
export STANDBY_PORT="${STANDBY_PORT:-55433}"
export CASC1_PORT="${CASC1_PORT:-55434}"   # replica1 (samurai) in cascade
export CASC2_PORT="${CASC2_PORT:-55435}"   # replica2 (stubble) in cascade

# ── Data directories ─────────────────────────────────────────────────────────
export WORK_DIR="${WORK_DIR:-$BENCH_ROOT/work}"
export PRIMARY_DATA="$WORK_DIR/primary"
export STANDBY_DATA="$WORK_DIR/standby"
export CASC1_DATA="$WORK_DIR/casc1"
export CASC2_DATA="$WORK_DIR/casc2"

# ── Benchmark parameters ─────────────────────────────────────────────────────
export RUNS="${RUNS:-5}"            # repetitions per scenario
export DURATION="${DURATION:-120}"   # seconds per pgbench run
export WARMUP="${WARMUP:-30}"        # warmup seconds
export WAL_SEG_SIZE="${WAL_SEG_SIZE:-16}"  # MB

# ── fsync throttle ──────────────────────────────────────────────────────────
export THROTTLE_SO="$WORK_DIR/fsync_throttle.so"
export THROTTLE_MS="${THROTTLE_MS:-0}"  # 0 = no throttle

# ── Replication slot names ───────────────────────────────────────────────────
SLOT_STANDBY="standby1_slot"
SLOT_CASC1="casc1_slot"
SLOT_CASC2="casc2_slot"

# ── Helper functions ─────────────────────────────────────────────────────────

log()   { echo "[$(date '+%H:%M:%S')] $*" >&2; }
fail()  { log "ERROR: $*"; exit 1; }

# psql wrappers
psql_p()  { local sql="$1"; shift; if [ "$sql" = "-f" ]; then psql -p "$PRIMARY_PORT"  -d postgres -At -f "$1" "${@:2}"; else psql -p "$PRIMARY_PORT"  -d postgres -At -c "$sql" "$@"; fi; }
psql_s()  { local sql="$1"; shift; if [ "$sql" = "-f" ]; then psql -p "$STANDBY_PORT"  -d postgres -At -f "$1" "${@:2}"; else psql -p "$STANDBY_PORT"  -d postgres -At -c "$sql" "$@"; fi; }
psql_c1() { local sql="$1"; shift; if [ "$sql" = "-f" ]; then psql -p "$CASC1_PORT"    -d postgres -At -f "$1" "${@:2}"; else psql -p "$CASC1_PORT"    -d postgres -At -c "$sql" "$@"; fi; }
psql_c2() { local sql="$1"; shift; if [ "$sql" = "-f" ]; then psql -p "$CASC2_PORT"    -d postgres -At -f "$1" "${@:2}"; else psql -p "$CASC2_PORT"    -d postgres -At -c "$sql" "$@"; fi; }

# Wrappers that accept a single SQL string via -c
psql_pc() { psql -p "$PRIMARY_PORT"  -d postgres -At -c "$1"; }
psql_sc() { psql -p "$STANDBY_PORT"  -d postgres -At -c "$1"; }

# Start a node, optionally with LD_PRELOAD throttle.
# When throttle is requested, start postgres directly (not via pg_ctl) so
# LD_PRELOAD is inherited by the walreceiver/flusher child processes.
# pg_ctl internally clears LD_PRELOAD in the forked postgres process.
start_node() {
    local data_dir="$1"
    local log_file="$2"
    local mode="${3:-}"

    if [ "$mode" = "throttle" ]; then
        log "Starting node (throttled, THROTTLE_MS=$THROTTLE_MS): $data_dir"
        # Start postgres directly — pg_ctl clears LD_PRELOAD.
        LD_PRELOAD="$THROTTLE_SO" THROTTLE_MS="$THROTTLE_MS" \
            postgres -D "$data_dir" -c logging_collector=on \
            >> "$log_file" 2>&1 &
        # Wait for postgres to be ready (up to 60s)
        local pid_file="$data_dir/postmaster.pid"
        for i in $(seq 1 60); do
            [ -f "$pid_file" ] && break
            sleep 1
        done
        [ -f "$pid_file" ] || fail "Server did not start: $data_dir"
    else
        log "Starting node: $data_dir"
        pg_ctl -D "$data_dir" -l "$log_file" start -w
    fi
}

stop_node() {
    local data_dir="$1"
    log "Stopping node: $data_dir"
    pg_ctl -D "$data_dir" stop -m fast -w 2>/dev/null || true
}

stop_all() {
    stop_node "$CASC2_DATA"
    stop_node "$CASC1_DATA"
    stop_node "$STANDBY_DATA"
    stop_node "$PRIMARY_DATA"
}

# Common postgresql.conf additions for benchmarking
common_conf() {
    cat <<'CONF'
listen_addresses = 'localhost'
shared_buffers = 1GB
max_connections = 200
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
CONF
}

# Wait for replication to be connected and streaming
# Timeout: 180s (increased from 60s for slow-disk throttle scenarios)
wait_for_streaming() {
    local port="$1"
    local app_name="$2"
    local timeout="${3:-180}"
    log "Waiting for standby '$app_name' to start streaming (timeout ${timeout}s)..."
    for i in $(seq 1 "$timeout"); do
        local state
        state=$(psql -p "$port" -d postgres -At -c \
            "SELECT state FROM pg_stat_replication WHERE application_name='$app_name'" 2>/dev/null || true)
        [ "$state" = "streaming" ] && { log "Streaming connected."; return 0; }
        sleep 1
    done
    fail "Standby '$app_name' did not start streaming within ${timeout}s"
}

# Reset IO stats on a node
reset_io_stats() {
    local port="$1"
    psql -p "$port" -d postgres -c "SELECT pg_stat_reset_shared('io');" >/dev/null 2>&1
}

# Compute WAL receive rate (bytes/sec) from start/end LSN
calc_recv_rate() {
    local start_lsn="$1"
    local end_lsn="$2"
    local elapsed="$3"
    psql -p "$STANDBY_PORT" -d postgres -At -c \
        "SELECT (pg_wal_lsn_diff('$end_lsn','$start_lsn')::bigint / ${elapsed}::numeric)::bigint"
}
