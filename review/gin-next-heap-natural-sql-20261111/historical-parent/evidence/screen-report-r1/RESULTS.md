# Heap fixed SQL and actual-AM screen

The independent prototype and its fixed-B comparator passed fresh clean builds, core regression tests and finite normal/assert qualification. This screen completed 576 raw / 432 retained / 144 warm observations. No repeat or tuning followed the results.

Independent recount passed 258 absolute groups, 258 pair groups and 1548 direct pairs. All metrics and comparisons are retained in the TSV files.
Percentages below are medians of six direct paired values, 100*(candidate/comparator-1); positive means slower. CPU cohorts remain separate. Exact B/T executable drift is shown without normalization. Absolute min/median/max/mean/sample SD/MAD accompany every metric.

## SQL executor

| Case | Cohort | B median ms [min,max] | Candidate median ms [min,max] | Candidate/B % | Candidate/T % | T/B % |
|---|---:|---:|---:|---:|---:|---:|
| heap_shared8 | 0 | 2.988500 [2.932000,3.108000] | 3.042500 [3.016000,3.130000] | +1.83 | +2.03 | +0.33 |
| heap_shared8 | 1 | 2.990000 [2.960000,3.049000] | 3.047000 [3.024000,3.104000] | +2.04 | +1.95 | +0.82 |
| heap_shared32 | 0 | 3.446000 [3.308000,3.471000] | 3.477500 [3.441000,3.605000] | +3.02 | +2.46 | +1.86 |
| heap_shared32 | 1 | 3.333500 [3.264000,3.349000] | 3.467000 [3.435000,3.498000] | +3.86 | +4.78 | -0.62 |
| heap_lossy8 | 0 | 40.128500 [39.981000,40.547000] | 40.583000 [40.261000,42.624000] | +1.04 | +1.71 | -0.99 |
| heap_lossy8 | 1 | 40.438000 [40.390000,40.936000] | 40.497500 [40.433000,40.671000] | +0.23 | -0.10 | +0.11 |
| heap_absent512 | 0 | 2.932000 [2.899000,2.964000] | 2.956500 [2.943000,2.991000] | +1.19 | +1.58 | -1.72 |
| heap_absent512 | 1 | 2.930500 [2.902000,2.954000] | 2.998000 [2.967000,3.022000] | +2.00 | +2.51 | -0.19 |
| seq_control | 0 | 57.928000 [55.623000,64.588000] | 56.612000 [54.635000,61.483000] | -2.52 | -1.48 | -0.57 |
| seq_control | 1 | 55.694500 [53.768000,57.188000] | 54.782500 [54.026000,57.242000] | -1.79 | -5.60 | +4.96 |

## Actual AM loop CPU

| Case | Cohort | B median ms [min,max] | Candidate median ms [min,max] | Candidate/B % | Candidate/T % | T/B % |
|---|---:|---:|---:|---:|---:|---:|
| am_or_dense1 | 0 | 9.731420 [9.718095,9.747880] | 9.874936 [9.844455,9.915381] | +1.58 | -0.14 | +1.60 |
| am_or_dense1 | 1 | 9.742062 [9.717684,9.789953] | 9.882192 [9.859767,9.901761] | +1.43 | +1.64 | -0.24 |
| am_or_dense2 | 0 | 11.067501 [11.031516,11.080099] | 11.178061 [11.149163,11.326429] | +1.09 | -1.61 | +2.68 |
| am_or_dense2 | 1 | 11.086609 [11.044937,11.228572] | 11.296554 [11.289374,11.342093] | +1.94 | +2.16 | -0.04 |
| am_or_dense7 | 0 | 19.343587 [19.318353,19.385234] | 19.592931 [19.518143,19.684804] | +1.33 | +0.40 | +0.91 |
| am_or_dense7 | 1 | 19.362465 [19.340427,19.410482] | 19.752344 [19.705675,19.826947] | +2.01 | +1.61 | +0.35 |
| am_or_dense8 | 0 | 20.958160 [20.907850,21.016193] | 18.434221 [18.379395,18.585514] | -11.98 | -12.35 | +0.34 |
| am_or_dense8 | 1 | 20.974253 [20.903192,21.044515] | 18.532344 [18.478283,18.559465] | -11.67 | -11.55 | -0.19 |
| am_or_dense32 | 0 | 68.867729 [68.786146,68.986988] | 53.309849 [53.138164,53.348046] | -22.65 | -22.24 | -0.55 |
| am_or_dense32 | 1 | 68.397909 [68.379166,68.497834] | 53.014100 [52.965943,53.105634] | -22.52 | -22.58 | +0.12 |
| am_or_dense128 | 0 | 255.063437 [254.853711,255.879822] | 183.047309 [182.373510,183.549518] | -28.32 | -27.86 | -0.55 |
| am_or_dense128 | 1 | 254.436709 [254.257800,254.670699] | 187.136281 [184.263910,187.531204] | -26.50 | -26.19 | -0.40 |
| am_or_dense512 | 0 | 1113.065115 [1111.091243,1113.789153] | 810.601298 [804.433741,812.956210] | -27.11 | -27.26 | +0.13 |
| am_or_dense512 | 1 | 1108.378162 [1103.467420,1111.123832] | 842.687072 [838.594749,845.062699] | -23.90 | -24.60 | +0.97 |

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
