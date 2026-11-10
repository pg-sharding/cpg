# Bitmap fixed SQL and actual-AM screen

The independent prototype and its fixed-B comparator passed fresh clean builds, core regression tests and finite normal/assert qualification. This screen completed 576 raw / 432 retained / 144 warm observations. No repeat or tuning followed the results.

Independent recount passed 240 absolute groups, 240 pair groups and 1440 direct pairs. All metrics and comparisons are retained in the TSV files.
Percentages below are medians of six direct paired values, 100*(candidate/comparator-1); positive means slower. CPU cohorts remain separate. Exact B/T executable drift is shown without normalization. Absolute min/median/max/mean/sample SD/MAD accompany every metric.

## SQL executor

| Case | Cohort | B median ms [min,max] | Candidate median ms [min,max] | Candidate/B % | Candidate/T % | T/B % |
|---|---:|---:|---:|---:|---:|---:|
| prefix_rare0 | 0 | 3.565500 [3.532000,3.747000] | 3.544500 [3.521000,3.563000] | -0.79 | -1.05 | +0.02 |
| prefix_rare0 | 1 | 3.547000 [3.498000,3.603000] | 3.537500 [3.485000,3.567000] | +0.04 | -1.67 | +0.72 |
| prefix_rare3 | 0 | 7.420000 [7.004000,7.861000] | 7.502500 [7.291000,7.788000] | +1.89 | +0.08 | +0.71 |
| prefix_rare3 | 1 | 7.295000 [6.939000,7.832000] | 7.700500 [7.336000,8.108000] | +6.53 | +1.82 | +3.16 |
| prefix_all | 0 | 32.383000 [32.171000,32.501000] | 32.890500 [32.664000,33.043000] | +1.62 | +1.05 | +0.01 |
| prefix_all | 1 | 32.516500 [32.232000,32.569000] | 33.056000 [32.912000,33.484000] | +1.61 | +2.13 | +0.24 |
| prefix_lossy | 0 | 33.435000 [33.250000,34.121000] | 33.023000 [32.900000,33.188000] | -1.46 | -1.37 | -0.01 |
| prefix_lossy | 1 | 33.569000 [33.445000,34.175000] | 33.048500 [32.763000,33.139000] | -2.09 | -0.95 | -0.89 |
| or_forced | 0 | 149.119500 [147.725000,151.296000] | 151.230000 [150.222000,152.534000] | +1.59 | +1.22 | +0.45 |
| or_forced | 1 | 148.883500 [148.376000,151.885000] | 154.978000 [151.237000,156.804000] | +3.45 | +3.71 | +0.04 |
| inline | 0 | 0.445000 [0.431000,0.495000] | 0.434000 [0.418000,0.446000] | -3.78 | -6.23 | -1.57 |
| inline | 1 | 0.437000 [0.422000,0.458000] | 0.452500 [0.432000,0.461000] | +1.05 | +6.21 | -2.68 |
| seq_control | 0 | 51.601500 [51.247000,52.897000] | 55.959000 [53.570000,63.163000] | +8.44 | +3.63 | +2.47 |
| seq_control | 1 | 54.952000 [52.208000,59.133000] | 56.893500 [53.346000,61.163000] | +3.24 | +1.58 | +1.21 |
| absent | 0 | 1.174500 [1.165000,1.208000] | 1.170500 [1.150000,1.228000] | -0.76 | -0.90 | +0.04 |
| absent | 1 | 1.162500 [1.155000,1.165000] | 1.155000 [1.152000,1.187000] | -0.43 | -0.13 | -0.17 |

## Actual AM loop CPU

| Case | Cohort | B median ms [min,max] | Candidate median ms [min,max] | Candidate/B % | Candidate/T % | T/B % |
|---|---:|---:|---:|---:|---:|---:|
| am_prefix_sparse | 0 | 1.819400 [1.798860,1.836727] | 1.803867 [1.796175,1.860191] | -0.79 | -1.33 | +1.33 |
| am_prefix_sparse | 1 | 1.801975 [1.788735,1.815314] | 1.799721 [1.783978,1.810247] | -0.07 | -0.62 | +0.25 |
| am_prefix_rare0 | 0 | 6.832840 [6.812534,6.879154] | 6.785744 [6.729330,6.847157] | -0.97 | -1.21 | +0.63 |
| am_prefix_rare0 | 1 | 6.813997 [6.798663,6.859784] | 6.732444 [6.716620,6.761217] | -1.24 | -1.44 | +0.22 |
| am_prefix_rare3 | 0 | 9.065817 [9.038075,9.109512] | 9.009096 [8.982861,9.056362] | -0.69 | -0.42 | -0.09 |
| am_prefix_rare3 | 1 | 9.057790 [9.019466,9.126988] | 9.014495 [8.988850,9.054249] | -0.48 | -0.27 | -0.21 |
| am_prefix_all | 0 | 25.342054 [25.285018,25.936577] | 25.305635 [25.288584,25.488995] | -0.15 | -0.27 | +0.24 |
| am_prefix_all | 1 | 25.316556 [25.289505,25.406831] | 25.292665 [25.207452,25.417207] | -0.06 | -0.70 | +0.42 |

## Scope and controls

The actual-AM loop calls index_rescan/index_getbitmap/tbm_free, including startup and consumption. Backend process CPU, client elapsed wall and SQL executor time are separate metrics. The synthetic fixture is shared-buffer warm. This is finite serial coverage, without a concurrency, source-causality or general merge claim. The candidates are independent alternatives over fixed B, not a patch series or a composition with C11.

All six owned cluster lifetimes stopped. Full source, installed trees, module, stopped seed and executed inputs remained unchanged. Full plan/actual-row/loop/recheck shape differences reported by the independent auditor: [].

Retained I/O counters (all roles, without trimming):

```json
{
  "0": {
    "Shared Read Blocks": 0,
    "Shared Dirtied Blocks": 0,
    "Shared Written Blocks": 0,
    "Temp Read Blocks": 0,
    "Temp Written Blocks": 0,
    "WAL Bytes": 0,
    "backend_read_bytes": 0,
    "backend_write_bytes": 0
  },
  "1": {
    "backend_read_bytes": 0,
    "backend_write_bytes": 0,
    "Shared Read Blocks": 0,
    "Shared Dirtied Blocks": 0,
    "Shared Written Blocks": 0,
    "Temp Read Blocks": 0,
    "Temp Written Blocks": 0,
    "WAL Bytes": 0
  }
}
```

The complete raw observations and full plans remain authoritative. No pooling, outlier removal, control correction, case deletion, new timing matrix or source tuning was used. The packet instructions distinguish original Linux execution from any static or offline replay checks.
