#!/bin/bash
# compare_throttle.sh — compare baseline vs new across throttle levels
# Usage:  ./compare_throttle.sh
# Reads results/throttle_matrix.csv (both variants appended to same file)

source "$(dirname "$0")/common.sh"

CSV="$RESULTS_DIR/throttle_matrix.csv"

if [ ! -f "$CSV" ]; then
    fail "Missing $CSV. Run ./run_throttle_matrix.sh first."
fi

echo "═══════════════════════════════════════════════════════════════════════════════════════"
echo "  Throttle matrix comparison: baseline vs new (flusher)"
echo "═══════════════════════════════════════════════════════════════════════════════════════"
printf "%-8s %10s %10s %8s %10s %10s %10s %10s %10s\n" \
    "ThrotMs" "Variant" "TPS" "WalB/s" "FlushLag" "ReplayLag" "FlushFsync" "WalRcvFsync" "FsyncTime"
echo "─────────────────────────────────────────────────────────────────────────────────────────"

# Read CSV, skip header
while IFS=, read -r label throttle_ms wal_bps wal_delta elapsed tps flush_lag replay_lag flusher_fsyncs flusher_fsync_time walrcv_fsyncs walrcv_fsync_time; do
    [ "$label" = "label" ] && continue
    variant=$(echo "$label" | sed 's/_throttle[0-9]*//')
    printf "%-8s %10s %10s %10s %10s %10s %10s %10s %10s\n" \
        "$throttle_ms" "$variant" "$tps" "$wal_bps" \
        "${flush_lag}s" "${replay_lag}s" \
        "$flusher_fsyncs" "$walrcv_fsyncs" "${walrcv_fsync_time}ms"
done < "$CSV" | sort -t, -k2 -n -k1 -n

echo "─────────────────────────────────────────────────────────────────────────────────────────"
echo ""

# Summary comparison per throttle level
echo "═══════════════════════════════════════════════════════════════════════════════════════"
echo "  Summary: flush_lag improvement (lower = better)"
echo "═══════════════════════════════════════════════════════════════════════════════════════"
printf "%-8s %15s %15s %10s\n" "ThrotMs" "Baseline flush" "New flush" "Reduction"
echo "─────────────────────────────────────────────────────────────────────────────────"

for THROTTLE in 0 1 10 50 100; do
    base_flush=$(grep "^baseline_throttle${THROTTLE}," "$CSV" 2>/dev/null | cut -d, -f7)
    new_flush=$(grep "^new_throttle${THROTTLE}," "$CSV" 2>/dev/null | cut -d, -f7)
    if [ -n "$base_flush" ] && [ -n "$new_flush" ]; then
        reduction=$(echo "scale=1; (1 - $new_flush / $base_flush) * 100" | bc -l 2>/dev/null)
        printf "%-8s %15s %15s %9s%%\n" "$THROTTLE" "${base_flush}s" "${new_flush}s" "$reduction"
    fi
done

echo ""
echo "═══════════════════════════════════════════════════════════════════════════════════════"
echo "  Summary: replay_lag (new build may be higher due to replay-before-flush)"
echo "═══════════════════════════════════════════════════════════════════════════════════════"
printf "%-8s %15s %15s\n" "ThrotMs" "Baseline replay" "New replay"
echo "─────────────────────────────────────────────────────────────────────────────────"

for THROTTLE in 0 1 10 50 100; do
    base_replay=$(grep "^baseline_throttle${THROTTLE}," "$CSV" 2>/dev/null | cut -d, -f8)
    new_replay=$(grep "^new_throttle${THROTTLE}," "$CSV" 2>/dev/null | cut -d, -f8)
    if [ -n "$base_replay" ] && [ -n "$new_replay" ]; then
        printf "%-8s %15s %15s\n" "$THROTTLE" "${base_replay}s" "${new_replay}s"
    fi
done
