# WAL Buffers Benchmark Suite

Benchmarks for lock-free WAL buffer communication between walreceiver and startup
process (walreceiver writes to `XLogCtl->pages`, startup reads from them without
disk I/O).

## Files

| File | Description |
|------|-------------|
| `bench_wb2.sh` | General benchmark: S0 (TPC-B), S3 (smalltx), S9 (walheavy) |
| `bench_wb_s2.sh` | S2: TPC-B with fsync throttle on standby |
| `bench_wb_uh.sh` | UH4: UPDATE-heavy (no table growth, frequent checkpoints) |
| `smalltx.sql` | S3 script: 1 INSERT per txn, 64 clients |
| `walheavy.sql` | S9 script: UPDATE + INSERT 100 rows, 32 clients |
| `prepare_tables.sql` | Create tables for smalltx/walheavy |
| `update_heavy.sql` | UH4 script: 20 UPDATEs × 640 bytes payload per txn |
| `prepare_update_heavy.sql` | Create 100K-row table for update_heavy |
| `fsync_throttle.c` | LD_PRELOAD library to simulate slow fsync on standby |

## Setup on VM

```bash
# Build fsync_throttle.so
gcc -shared -fPIC -o fsync_throttle.so fsync_throttle.c -ldl
mkdir -p ~/bench_wb/lib
cp fsync_throttle.so ~/bench_wb/lib/

# Copy scripts and SQL
cp bench_wb2.sh bench_wb_s2.sh bench_wb_uh.sh ~/bench_wb/
cp *.sql ~/bench_wb/
chmod +x ~/bench_wb/bench_wb*.sh

# Build both variants
# baseline: original code (walrcvflusher, no wal buffers)
cd ~/cpg && make -j8 && make install DESTDIR=~/bench_wb/baseline/pginst
# mine: with wal buffers patch
cd ~/mycpg && make -j8 && make install DESTDIR=~/bench_wb/mine/pginst
```

## Running benchmarks

```bash
# S0: TPC-B (32 clients, 60s, 3 runs)
for r in 1 2 3; do ~/bench_wb/bench_wb2.sh baseline baseline_S0_r$r; done
for r in 1 2 3; do ~/bench_wb/bench_wb2.sh mine mine_S0_r$r; done

# S3: smalltx (64 clients, 60s)
for r in 1 2 3 4; do ~/bench_wb/bench_wb2.sh baseline baseline_S3_r$r; done
for r in 1 2 3 4; do ~/bench_wb/bench_wb2.sh mine mine_S3_r$r; done

# S9: walheavy FPI (32 clients, 60s)
for r in 1 2; do ~/bench_wb/bench_wb2.sh baseline baseline_S9_r$r; done
for r in 1 2; do ~/bench_wb/bench_wb2.sh mine mine_S9_r$r; done

# S2: TPC-B + fsync throttle
for ms in 5 20 50 100; do
  THROTTLE_MS=$ms ~/bench_wb/bench_wb_s2.sh baseline baseline_S2_t$ms
  THROTTLE_MS=$ms ~/bench_wb/bench_wb_s2.sh mine mine_S2_t$ms
done

# UH4: UPDATE-heavy (32 clients, 60s)
for r in 1 2 3; do ~/bench_wb/bench_wb_uh.sh baseline baseline_UH4_r$r 32 60; done
for r in 1 2 3; do ~/bench_wb/bench_wb_uh.sh mine mine_UH4_r$r 32 60; done
```

## Results

| Scenario | Baseline MB/s | Mine MB/s | Ratio | Notes |
|----------|-------------|-----------|-------|-------|
| S0 TPC-B (32c) | 1.76 | 1.88 | **1.07x** | Low WAL, high variance |
| S3 smalltx (64c) | 18.12 | 18.07 | 1.00x | CPU-bound |
| S9 walheavy FPI (32c) | 44.75 | 47.25 | **1.06x** | WAL-heavy |
| S2 TPC-B + throttle 5ms | 1.81 | 1.81 | 1.00x | Throttle=fsync, not read |
| S2 TPC-B + throttle 100ms | 1.83 | 1.83 | 1.00x | |
| UH4 UPDATE-heavy (32c) | 70.87 | 70.78 | 1.00x | Bottleneck=primary CPU |

### pg_stat_io on standby (UH4, 60s)

| Metric | Baseline | Mine |
|--------|---------|------|
| startup WAL reads | 650,342 | **4** |
| startup read_time | 2340ms | **0.033ms** |
| walreceiver writes | 39,256 | **0** |
| walreceiver fsyncs | 304 | **0** |
| walrcvflusher fsyncs | 233 | **0** |

The patch eliminates all WAL disk I/O on standby — startup reads from WAL
buffers instead of disk. WAL rate is unchanged because the bottleneck shifts
to primary CPU (WAL generation), not standby WAL read.
