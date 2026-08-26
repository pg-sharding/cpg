#!/bin/bash
# compare.sh — compare baseline vs new results from ALL.csv
# Usage:  ./compare.sh
# Reads results/baseline/ALL.csv and results/new/ALL.csv

source "$(dirname "$0")/common.sh"

BASELINE_CSV="$RESULTS_DIR/baseline/ALL.csv"
NEW_CSV="$RESULTS_DIR/new/ALL.csv"

if [ ! -f "$BASELINE_CSV" ] || [ ! -f "$NEW_CSV" ]; then
    fail "Missing ALL.csv files. Run ./matrix.sh baseline and ./matrix.sh new first."
fi

echo "══════════════════════════════════════════════════════════════════════════"
echo "  walrcvflusher benchmark comparison: baseline vs new"
echo "══════════════════════════════════════════════════════════════════════════"
printf "%-40s %15s %15s %10s %10s\n" "Scenario" "baseline B/s" "new B/s" "ratio" "verdict"
echo "─────────────────────────────────────────────────────────────────────────"

# Read scenarios from new CSV (they should match baseline)
while IFS=, read -r label bps delta elapsed; do
    # Extract scenario base name (strip _runN suffix)
    base=$(echo "$label" | sed 's/_run[0-9]*//')

    # Skip header
    [ "$label" = "label" ] && continue

    # Find matching baseline entry (same scenario, average across runs)
    baseline_bps=$(grep "^${base}_run" "$BASELINE_CSV" 2>/dev/null | cut -d, -f2 | \
                   awk '{sum+=$1; n++} END {if(n>0) printf "%.0f", sum/n}')
    new_bps=$(grep "^${base}_run" "$NEW_CSV" 2>/dev/null | cut -d, -f2 | \
              awk '{sum+=$1; n++} END {if(n>0) printf "%.0f", sum/n}')

    if [ -z "$baseline_bps" ] || [ -z "$new_bps" ]; then
        continue
    fi

    ratio=$(echo "scale=2; $new_bps / $baseline_bps" | bc -l)
    verdict="OK"
    if (( $(echo "$ratio > 1.05" | bc -l) )); then
        verdict="WIN"
    elif (( $(echo "$ratio < 0.95" | bc -l) )); then
        verdict="REGRESSION"
    fi

    printf "%-40s %15s %15s %10s %10s\n" "$base" "$baseline_bps" "$new_bps" "${ratio}x" "$verdict"
done < "$NEW_CSV" | sort -u

echo "─────────────────────────────────────────────────────────────────────────"
echo ""
echo "pg_stat_io verification (new build):"
echo "  Check results/new/*/pg_stat_io.txt for:"
echo "    walreceiver:  writes>0, fsyncs=0  (writes WAL, no fsync)"
echo "    walrcvflusher: fsyncs>0, writes=0 (fsyncs WAL, no writes)"
echo ""
echo "  On baseline (no flusher): walreceiver should have writes>0 AND fsyncs>0"
echo "  and there should be NO walrcvflusher row."
