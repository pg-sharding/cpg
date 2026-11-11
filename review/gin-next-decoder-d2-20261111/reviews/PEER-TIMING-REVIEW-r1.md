# Независимый read-only peer review D2 timing capsule r1

Проверено 2026-11-11. **PASS статического peer review; блокирующих ошибок в просмотренном capsule не найдено.** Это не PASS actual smoke, разрешение run или результат производительности. По последнему сообщению root import/prepare начат, smoke/run ещё не запускались. Root отдельно проверяет campaign/run/importer и владеет live gate.

Объект: `timing-prep-r1/` с bindings из `TIMING-INPUTS-D2-r1.json`. Повторно проверены все13 manifest entries по размеру и SHA256. Скрипты, frozen файлы, VM, backend и бенчмарки не изменялись/не запускались. Выполнены только чтение исходников, сравнение текстов/hash и локальные чистые Python/AST/JSON вычисления матрицы, расписания и codec expectation. Actual raw/smoke output в этом peer review не проверялся: такого локального набора здесь нет.

## Матрица и provenance

18 decoder cases и их loops точно совпадают с прежним `startup-decoder/screen/protocol.py`; список отдельно совпадает с константами нового independent auditor. Это не новая сетка, подобранная по результату. Сохранены one/tail1–3, batch4/5/8, dense128/4096/multi, first-singleton growth, singletons и delta2–7.

Все7 SQL case records, после удаления добавленного `kind`, точно совпадают с прежними K3 qualification inputs: skew1000, dense_and, or_forced, single_forced, single_rare, prefix, seq_control. Это whole commands с прежним числом probes100/10/5/5/100/100/5 соответственно. Время не делится на probes; LATERAL batch не равен независимым клиентским запросам.

`qualification/decoder-native.c` byte-identical прежнему D1 decoder module: SHA256 `070f4a02daf4b2f0e509e396fa7cad7e0387760a68901dd2381b94798b5d333b`. `session.py`, `common.py`, `validate.py` byte-identical old K3 timing capsule. Изменения `analyze.py` соответствуют новой матрице и трём метрикам каждого case; остаточный generic AM branch не создаёт AM workload, поскольку протокол и independent auditor требуют ровно7 SQL +18 decoder.

Independent audit не импортирует runner, protocol, analyzer или validator. Он имеет собственные constants, строит ожидаемые TID и считает varbyte lengths через repeated division, тогда как protocol использует bit lengths. Третьей локальной проверкой заново получены все18 размеров, segment counts, checksums и consumed totals из PROTOCOL.json. Использованы подтверждённые baseline codec constants:11 offset bits, header8 байт, round-up до чётного размера, максимум7 bytes per integer. Все построенные blocks меньше InvalidBlockNumber, offsets валидны; delta7 ограничен двумя TID, поэтому block shift31 не переполняет uint32.

## Расписание и счётчики

Roles `[B,T,D1,D2]`, Williams base `[0,1,3,2]`, четыре cyclic shifts ×3. Независимо пересчитано: среди12 retained rounds каждая роль находится в каждой позиции3 раза, каждая directed adjacent pair встречается3 раза. Два warm rounds используют первые два orders, после чего retained расписание начинает полный12-round block. Полная последовательность вместе с warm не обязана быть сбалансирована; warm исключены из statistics. Cohort1 разворачивает case order, но не переизобретает role schedule.

| Величина | Один cohort | Всего2 cohorts |
|---|---:|---:|
| measured raw:25×4×14 | 1400 | 2800 |
| retained:25×4×12 | 1200 | 2400 |
| warm:25×4×2 | 200 | 400 |
| absolute groups:25×4×3 | 300 | 600 |
| pair groups:25×6×3 | 450 | 900 |
| direct round pairs:450×12 | 5400 | 10800 |

Smoke отдельно:25×4=100 measured commands,0 retained/accepted. Каждому measured command предшествует отдельный literal query, поэтому2800 — число measured raw observations, не общее число всех SQL-вызовов. Oracle queries и literal warming не входят в2800. Поле `accepted_timing_samples=1400` у завершённого cohort включает валидированные warm raw observations; для статистического retained набора используется1200. Эти значения в runner/analyzer/auditor согласованы, но при публикации следует сохранять явное разделение raw/retained/warm.

## Единицы, decoder и SQL

Три metrics на case действительно различны:

- `backend_cpu_ms`: `/proc/PID/schedstat cpu_ns / 1e6`, whole measured command;
- `client_wall_ms`: monotonic command span /1e6, без JSON parsing и `/proc` reads;
- SQL: JSON `EXPLAIN Execution Time`, уже в ms; decoder: собственный `CLOCK_PROCESS_CPUTIME_ID` interval, уже в ms.

Native inner interval включает фактический backend `ginPostingListDecodeAllSegments`, palloc/repalloc, materialization, consumed update и pfree каждой итерации. Подготовка TID, compression и полный generated-TID oracle выполняются вне этого inner interval. Whole-command CPU/wall включают эти дополнительные стадии. Их нельзя смешивать с inner decoder CPU или суммировать как независимые gains. Это actual backend decoder через квалифицированный module, без утверждения о полном actual-AM покрытии.

До timed loop native module полностью сравнивает decoded list с независимо сгенерированными TID и проверяет порядок/checksum; в цикле сохраняется consumed dependency. Auditor проверяет loops, item count, bytes, segments, checksum, consumed и положительное конечное decoder CPU как у literal, так и measured вызова. Он не притворяется, что checksum заново вычислен внутри каждой timed iteration.

SQL acceptance проверяет literal aggregate по fixed answers, root Actual Rows=1/Loops=1 и выбранный index/probe count либо Seq Scan без indexes. Runner фиксирует полный semantic plan с фактическими rows/loops/rechecks после удаления стоимостей, времён и buffer/I/O/WAL counters. Independent auditor заново строит такой signature и требует равенства между ролями и cohorts. Плановые estimates исключены; actual cardinality и recheck counters сохранены. Это сильнее одной проверки имени index.

Дополнительно runner выполняет ordered Seq/index comparisons для всех25 qualification SQL cases и4 roles, то есть100 сравнений за cohort/smoke. Auditor проверяет PASS, число100 и равенство actual/reference digests для всех записей. Само равенство ordered rows между ролями обеспечивается runner; independent audit не реконструирует строки из сохранённых hashes. Такая граница не меняет scope квалификации, но не должна описываться как повторное чтение полного SQL output из одного digest.

## Независимый пересчёт и границы доказательств

`audit-independent-r1.py` проверяет every raw/literal row и schedule, включая warm; reconstructs300 absolute и450 pair groups на cohort, все12 direct round pairs каждой группы. Median/MAD/stdev/mean/differences/percentages рассчитываются независимо, finite/positive checks выполняются до statistics. Все6 role pairs, включая B/T и D2/D1, сохраняются. Нет pooling cohorts, trimming, baseline normalization, significance либо causal inference. Неравенство против exact twin остаётся наблюдением.

B/T identity проверяется по prefix, backend SHA и module SHA. Raw/literal hashes привязаны к status, analysis hashes записываются в independent receipt. Полный source/install/PID/unused-copy/seed binding остаётся также обязанностью campaign и root live review; offline арифметический auditor не заменяет эти проверки.

Два уточнения к будущему actual smoke review, **не причины менять frozen capsule**:

1. **Chronology.** Auditor требует `start_monotonic_ns >= previous start + client_ns` для measured spans, в том числе между cohorts. Literal journal имеет только realtime timestamp; measured row имеет monotonic start и realtime end. Из этих clocks нельзя строго восстановить `literal < measured start`. Проверяется более слабое `literal realtime <= measured realtime end`. Последовательность durable literal → measured явно следует из исходника runner. Root подтвердил эту границу; не следует писать, что raw alone доказывает точную межчасовую связь начала.
2. **Settings.** Smoke reviewer проверяет равенство всех per-case settings между ролями, но не утверждает ожидаемые значения каждого поля. Full independent auditor дополнительно утверждает jit/memoize/parallel/fuzzy/timeouts/work_mem и равенство settings между cohorts; search_path/scan-enable flags всё равно требуют осмысленного сравнения с frozen cases. Root сообщил, что выполнит явную проверку ожидаемых settings при actual smoke review. Проверка реального SQL plan остаётся обязательной.

Пока нет actual output, нельзя объявлять `PASS_INDEPENDENT_D2_SMOKE_RECOUNT` или `PASS_INDEPENDENT_COMPLETE_RECOUNT`: текущий PASS относится только к этому source/protocol review. Готовый capsule совместим с намеченным prepare→smoke→external review→run порядком, при сохранении root gate и перечисленных оговорок. Новых исходников или обязательств по AM/rescan этот peer review не добавляет.
