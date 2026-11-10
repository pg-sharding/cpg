# Independent offline Heap wide SQL auditor

New audit-independent-r1.py imports no benchmark code, executes no PostgreSQL
command and performs no VM operation. Its new code is AST/help/source checked
only until actual collected smoke/screen data is supplied. It independently
reconstructs exact old expression bytes, IDs1..200000/count/sum, forced ordered
Seq/GIN plans, literal/raw journals, all role/round/case/birth mappings, frozen
bindings, backend metadata, recorded cleanup and all numeric statistics.
It does not claim actual live PID/source/seed inventories; root supplies a
separate live proof. No timing analysis is performed in smoke mode.

Run locally, adjusting only collected path/output locations:

```sh
I=review/gin-next-20261110/heap-wide-sql-followup-r1
O=review/gin-next-20261110/or-consistent/or/timing-r1/harness/inputs/timing-cases.json
python3 -B "$I/audit-independent-r1.py" --inputs "$I" --old-am-inputs "$O" \
  --results /absolute/path/smoke-collected/run-r1 --mode smoke \
  --out-new /absolute/path/SMOKE-INDEPENDENT-AUDIT-r1.json
```

Only after complete accepted PASS and frozen analyzer outputs:

```sh
python3 -B "$I/audit-independent-r1.py" --inputs "$I" --old-am-inputs "$O" \
  --results /absolute/path/screen-collected/run-r1 --mode screen \
  --analysis0 /absolute/path/analysis0 --analysis1 /absolute/path/analysis1 \
  --out-new /absolute/path/SCREEN-INDEPENDENT-AUDIT-r1.json
```

Expected screen per cohort:192 raw,144 retained,48 warm,72 absolute groups,
72 same-round pair groups,432 direct pairs. Smoke is24 raw/0 retained. The
full screen is384/288/96,144 absolute groups,144 pairs and864 direct pairs;
all3 metrics and all3 pairs remain. Own median/fsum/sample-variance/MAD code
recomputes every absolute/range/direct ratio/difference statistic and compares
JSON fields with explicit finite tolerances. No filter or normalization.
The output is a new SHA-bound JSON receipt file, never an overwritten result.
