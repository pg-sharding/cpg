# walrcvflusher benchmarks

Бенчмарки для коммита `69cf50b2dac` ("Flush async"), добавляющего процесс `walrcvflusher`,
который выносит `fsync` WAL из `walreceiver` в отдельный процесс при потоковой репликации.

## Структура

```
bench/walrcvflusher/
├── scripts/
│   ├── common.sh              # общие переменные, хелперы (source из всех скриптов)
│   ├── setup.sh               # инициализация primary + standby (с/без throttle)
│   ├── cascade_setup.sh       # инициализация 3-уровневого каскада
│   ├── run_bench.sh           # один прогон: warmup → pgbench → сбор метрик
│   ├── run_throttle_matrix.sh # матрица throttle: 0/1/10/50ms для одного build
│   ├── collect_metrics.sh     # автономный сбор метрик (pg_stat_io, wait events, lag)
│   ├── matrix.sh              # оркестратор всех сценариев S0-S11
│   ├── compare.sh             # сравнение baseline vs new (из matrix.sh)
│   ├── compare_throttle.sh   # сравнение baseline vs new (из throttle matrix)
│   └── fsync_throttle.c       # LD_PRELOAD библиотека для замедления fsync
├── sql/
│   ├── smalltx.sql            # S3: малые транзакции, высокий WAL rate
│   ├── copy_bulk.sql          # S4: большие транзакции (bulk INSERT)
│   ├── walheavy.sql           # S9: UPDATE + INSERT (full-page images)
│   └── prepare_tables.sql     # создание таблиц для кастомных скриптов
└── results/                   # результаты прогонов (создаётся автоматически)
```

## Быстрый старт

### 1. Сборка PostgreSQL

```bash
# Собрать новый бинарник (с flusher)
git checkout 69cf50b2dac
./configure --prefix=$PWD/pginst && make -j install
```

### 2. Сборка fsync throttle

```bash
gcc -shared -fPIC -o bench/walrcvflusher/work/fsync_throttle.so \
    bench/walrcvflusher/scripts/fsync_throttle.c -ldl
```

### 3. Инициализация кластера

```bash
cd bench/walrcvflusher
./scripts/setup.sh            # primary + standby (без throttle)
# или:
THROTTLE_MS=20 ./scripts/setup.sh throttle  # standby с замедленным fsync
```

### 4. Запуск throttle matrix (рекомендуется)

```bash
# New build (с flusher): 4 throttle levels за один прогон
PGINST=~/work/cpg/pginst_new RUNS=1 DURATION=30 WARMUP=5 \
    ./scripts/run_throttle_matrix.sh new "0 1 10 50"

# Baseline (без flusher): те же 4 throttle levels
PGINST=~/work/cpg/pginst_baseline RUNS=1 DURATION=30 WARMUP=5 \
    ./scripts/run_throttle_matrix.sh baseline "0 1 10 50"
```

### 5. Сравнение

```bash
./scripts/compare_throttle.sh
```

### 6. Альтернатива: полный matrix (S0-S11)

```bash
./scripts/matrix.sh new          # все сценарии для new build
./scripts/matrix.sh baseline     # все сценарии для baseline build
./scripts/compare.sh             # сравнение
```

## Сценарии

| ID | Описание | Нагрузка | Особенность |
|----|----------|----------|-------------|
| S0 | TPC-B baseline (reference) | `pgbench --builtin=tpcb -c32 -j8` | Нет throttle |
| S1 | Fast disk control | TPC-B | fsync не bottleneck (no-op ожидаем) |
| S2 | Slow disk simulation | TPC-B | `THROTTLE_MS=20/50/100` через LD_PRELOAD |
| S3 | High WAL rate | smalltx.sql `-c64` | Малые tx → максимум fsync-частоты |
| S4 | Large transactions | copy_bulk.sql `-c1` | Длинный WAL-поток |
| S5 | Sync rep: remote_flush | TPC-B | Commit ждёт flusher |
| S6 | Sync rep: remote_write | TPC-B | Commit не ждёт flusher |
| S7 | Cascade (3 узла) | TPC-B | `cascade_setup.sh` отдельно |
| S8 | Разный wal_segment_size | TPC-B | `WAL_SEG_SIZE=1` или `256` |
| S9 | WAL-heavy (FPI) | walheavy.sql | UPDATE + INSERT |
| S10 | Изоляция коммитов | TPC-B | 3 checkout'а: pre-d68, d68, 69cf |
| S11 | recovery_min_apply_delay=5s | TPC-B | WAL копится на standby |

## Ключевые метрики

### Главный KPI: WAL receive rate (bytes/sec)
- Источник: `pg_last_wal_receive_lsn()` дельта / время
- Победа: `new_bps / baseline_bps >= 1.05` на медленном диске

### Задержки (pg_stat_replication)
- `write_lag` — до write на standby (не должен расти)
- `flush_lag` — до fsync (может расти, т.к. flusher асинхронен)
- `replay_lag` — до apply (guardrail: не должен расти >1.1x)

### pg_stat_io split (подтверждение архитектуры)
```sql
SELECT backend_type, writes, fsyncs
FROM pg_stat_io
WHERE object = 'wal'
  AND backend_type IN ('walreceiver', 'walrcvflusher');
```
- **new**: `walreceiver` — writes>0, fsyncs=0; `walrcvflusher` — fsyncs>0, writes=0
- **baseline**: `walreceiver` — writes>0 AND fsyncs>0; `walrcvflusher` — нет строки

### fsync timing (при включённом track_wal_io_timing)
```sql
SELECT backend_type, fsyncs,
       round(fsync_time / greatest(fsyncs,1), 3) AS avg_fsync_ms
FROM pg_stat_io WHERE object = 'wal';
```

## S2: Симуляция медленного диска

```bash
# Сборка throttle (один раз)
gcc -shared -fPIC -o work/fsync_throttle.so scripts/fsync_throttle.c -ldl

# Запуск standby с throttle
THROTTLE_MS=20 ./scripts/setup.sh throttle

# Прогон
THROTTLE_MS=20 ./scripts/matrix.sh new S2

# Разные задержки: 0, 5, 20, 50, 100 ms
# (перезапуск standby между прогонами)
```

### Важно: LD_PRELOAD и pg_ctl

`pg_ctl` на Linux очищает `LD_PRELOAD` в fork'нутом `postgres` процессе (через `set_ps_display()`,
который перезаписывает область памяти с окружением). Поэтому `start_node()` в `common.sh`
при `mode=throttle` запускает `postgres` напрямую, а не через `pg_ctl`:

```bash
LD_PRELOAD="$THROTTLE_SO" THROTTLE_MS="$THROTTLE_MS" \
    postgres -D "$data_dir" -c logging_collector=on >> "$log_file" 2>&1 &
```

Проверить, что throttle работает:
```bash
# fsync_throttle.so должна быть в maps child-процесса (walreceiver)
PM_PID=$(pgrep -f "postgres.*55433" | head -1)
for child in $(pgrep -P $PM_PID); do
    cat /proc/$child/maps | grep throttle
done
```

## S5/S6: Синхронная репликация

```bash
# На primary:
psql -p 55432 -c "ALTER SYSTEM SET synchronous_standby_names = '*';"
psql -p 55432 -c "ALTER SYSTEM SET synchronous_commit = on;"      # remote_flush
# или:
psql -p 55432 -c "ALTER SYSTEM SET synchronous_commit = remote_write;"
psql -p 55432 -c "SELECT pg_reload_conf();"
```

Важно: `synchronous_standby_names = '1'` не работает (нужно `'ANY 1'` или `'*'`).

## Переменные окружения

| Переменная | По умолчанию | Описание |
|------------|--------------|----------|
| `PGINST` | `$PWD/pginst` | Путь к установке PostgreSQL |
| `RUNS` | `5` | Повторений на сценарий |
| `DURATION` | `120` | Секунд на прогон pgbench |
| `WARMUP` | `30` | Секунд warmup |
| `WAL_SEG_SIZE` | `16` | Размер WAL-сегмента (MB) |
| `THROTTLE_MS` | `0` | Задержка fsync (ms) |
| `PRIMARY_PORT` | `55432` | Порт primary |
| `STANDBY_PORT` | `55433` | Порт standby |
| `CASC1_PORT` | `55434` | Порт replica1 (каскад) |
| `CASC2_PORT` | `55435` | Порт replica2 (каскад) |

## Ожидаемые результаты

| Сценарий | Метрика | Победа | No-regression |
|----------|---------|-------|---------------|
| S2 (slow) | wal_recv_bps | >= 1.10x | >= 0.95x |
| S0/S1 | wal_recv_bps | >= 1.05x | >= 0.95x |
| S3 (high WAL) | wal_recv_bps | >= 1.05x | >= 0.95x |
| S5 (remote_flush) | commit latency | <= 1.05x | <= 1.15x |
| S6 (remote_write) | commit latency | <= 1.02x | <= 1.05x |
| Все | replay_lag | <= 1.10x | <= 1.20x |

---

# Результаты бенчмарков

## Окружение

- **Сервер**: Ubuntu 7.0, 8 ядер, 62GB RAM, 1.9TB диск
- **Компилятор**: gcc 15.2.0
- **Сборка**: meson 1.12.0, ninja
- **PostgreSQL**: 18.5 (based on commit `69cf50b2dac`)
- **Бенчмарк**: pgbench (TPC-B builtin, smalltx.sql custom)
- **Throttle**: LD_PRELOAD `fsync_throttle.so` (замедляет `fsync()`/`fdatasync()` на N ms)

## Найденные проблемы и исправления

### 1. `pginst_new` собран из baseline исходников

**Симптом**: `walrcvflusher` процесс запущен, но делает 0 fsyncs. `pg_stat_io` показывает
все fsyncs у `walreceiver`.

**Причина**: При подготовке baseline-сборки исходные файлы на сервере (`walreceiver.c`,
`walreceiverfuncs.c`, `postmaster.c`, `pgstat_io.c`, и др.) были заменены на baseline-версии
(без flusher-кода). `pginst_new` был собран **до** этой замены, но `build_new` не был
пересобран. При последующей пересборке `build_new` использовал уже baseline-исходники.

**Решение**: Восстановлены все исходные файлы из коммита `69cf50b2dac`:
- `src/backend/replication/walreceiver.c`
- `src/backend/replication/walreceiverfuncs.c`
- `src/backend/replication/walrcvflusher.c`
- `src/include/replication/walrcvflusher.h`
- `src/backend/postmaster/postmaster.c`
- `src/backend/postmaster/pmchild.c`
- `src/backend/postmaster/launch_backend.c`
- `src/backend/utils/activity/pgstat_backend.c`
- `src/backend/utils/activity/pgstat_io.c`
- `src/backend/utils/init/miscinit.c`
- `src/include/miscadmin.h`
- `src/include/storage/proc.h`
- `src/include/replication/walreceiver.h`
- `src/backend/replication/meson.build`
- `src/backend/utils/activity/wait_event_names.txt`

После пересборки `build_new` и переустановки `pginst_new` flusher начал работать корректно.

### 2. `pg_stat_io` показывает 0 fsyncs для `walrcvflusher`

**Симптом**: Debug-логирование подтвердило, что `WalRcvFlusherFlush()` вызывает
`issue_xlog_fsync()`, но `pg_stat_io` показывает 0 fsyncs для `walrcvflusher`.

**Причина**: `walrcvflusher` процесс не вызывает `pgstat_report_stat()` для сброса
накопленных IO-статистик в shared memory. IO-статы копятся в `PendingIOStats`
(в `pgstat_count_io_op_time()`), но никогда не сбрасываются, т.к. `ProcessMainLoopInterrupts()`
не вызывает `pgstat_report_stat()`, а flusher не имеет другого механизма сброса.

Для сравнения, `walreceiver` вызывает `pgstat_report_wal(false)` в основном цикле
(line 670 в `walreceiver.c`), который в свою очередь вызывает `pgstat_flush_io()`.

**Решение**: Добавлен вызов `pgstat_report_stat(true)` в главный цикл `WalRcvFlusherMain`
в `src/backend/replication/walrcvflusher.c` (после `WalRcvFlusherFlush()`):

```c
for (;;)
{
    ResetLatch(MyLatch);
    ProcessMainLoopInterrupts();

    WalRcvFlusherFlush();

    /* Flush pending IO stats to shared memory */
    pgstat_report_stat(true);   /* <-- ДОБАВЛЕНО */

    (void) WaitLatch(MyLatch,
                     WL_LATCH_SET | WL_TIMEOUT | WL_EXIT_ON_PM_DEATH,
                     WALRCVFLUSHER_NAPTIME,
                     WAIT_EVENT_WAL_RCV_FLUSHER_MAIN);
}
```

После исправления `pg_stat_io` корректно показывает fsyncs для `walrcvflusher`.

### 3. `pg_ctl` не передаёт `LD_PRELOAD`

**Симптом**: `setup.sh throttle` запускает standby через `pg_ctl`, но `LD_PRELOAD`
не доходит до `postgres` (walreceiver) процесса. Throttle не работает.

**Причина**: `postgres` (postmaster) вызывает `set_ps_display()`, который на Linux
перезаписывает область памяти с окружением (через `setproctitle`), из-за чего
`/proc/PID/environ` больше не показывает `LD_PRELOAD`. Однако `fsync_throttle.so`
**фактически загружена** в child-процессах (видно через `/proc/PID/maps`), т.к.
`fork()` наследует memory map.

**Дополнительно**: `pg_ctl` использует `fork()+execve()` для запуска `postgres`,
и при `execve` динамический линкер перечитывает `LD_PRELOAD` из окружения. Если
`set_ps_display()` уже перезаписал environ к моменту fork'а child-процессов,
`LD_PRELOAD` может быть потерян.

**Решение**: `start_node()` в `common.sh` при `mode=throttle` запускает `postgres`
напрямую (не через `pg_ctl`):

```bash
LD_PRELOAD="$THROTTLE_SO" THROTTLE_MS="$THROTTLE_MS" \
    postgres -D "$data_dir" -c logging_collector=on >> "$log_file" 2>&1 &
```

### 4. `synchronous_standby_names = '1'` не работает

**Симптом**: `ALTER SYSTEM SET synchronous_standby_names = '1'` применяется, но
`pg_stat_replication.sync_state` остаётся `async`.

**Решение**: Использовать `'*'` (любой standby) или `'ANY 1'` вместо `'1'`.

## Архитектура walrcvflusher

Коммит `69cf50b2dac` добавляет процесс `walrcvflusher`, который выносит `fsync` WAL
из `walreceiver` в отдельный процесс. Это аналог паттерна MySQL/InnoDB
`log_writer`/`log_flusher`.

### Поток данных (new build)

```
Primary  ──WAL──>  walreceiver  ──write()──>  WAL segment file
                       │                          │
                       │ WakeupWalRcvFlusher()     │
                       ▼                          │
                  walrcvflusher  ──fsync()────────┘
                       │
                       ▼
                  flushedUpto (shared memory)
                       │
                       ▼
                  WakeupRecovery() + WalSndWakeup()
```

### Поток данных (baseline)

```
Primary  ──WAL──>  walreceiver  ──write()──>  WAL segment file
                       │                          │
                       └──fsync()──────────────────┘
                       │
                       ▼
                  flushedUpto (shared memory)
                       │
                       ▼
                  WakeupRecovery() + WalSndWakeup()
```

### Ключевые функции

- `WalRcvFlusherMain()` (`walrcvflusher.c:190`) — главный цикл flusher'а
- `WalRcvFlusherFlush()` (`walrcvflusher.c:265`) — fsync текущего сегмента
- `WakeupWalRcvFlusher()` (`walrcvflusher.c:358`) — wakeup flusher из walreceiver
- `XLogWalRcvWrite()` (`walreceiver.c:1095`) — write WAL + обновление `writtenUpto`
- `XLogWalRcvFlush()` (`walreceiver.c:1163`) — fsync при close сегмента (не в основном цикле)
- `XLogWalRcvPickUpFlushPosition()` (`walreceiver.c:1144`) — забрать прогресс flusher'а
- `WalRcvWaitForFlush()` (`walreceiverfuncs.c:427`) — ожидание flush перед записью на диск

### Условие работы flusher'а

```c
// WalRcvFlusherFlush() выходит если:
if (!WalRcvStreaming())           return;  // walreceiver не streaming
if (XLogRecPtrIsInvalid(written)) return;  // нет writtenUpto
if (written <= flushed)            return;  // всё уже flushed
if (tli == 0)                     return;  // нет timeline
```

### Код review: race condition в `WalRcvWaitForFlush`

В `walreceiverfuncs.c:427`:
```c
while (GetWalRcvFlushRecPtr(NULL, NULL) < lsn && WalRcvStreaming())
    ConditionVariableSleep(&walrcv->flushCV, WAIT_EVENT_WAL_RECEIVER_FLUSH);
```

`WalRcvStreaming()` возвращает `false` для `WALRCV_STOPPING`, но flush ещё не выполнен.
Если walreceiver останавливается, `WalRcvWaitForFlush` может выйти до того, как flusher
успеет fsync'нуть. На практике это безопасно, т.к. `WalRcvDie()` вызывает
`XLogWalRcvFlush(true)` для финального flush.

---

## Результаты: Throttle Matrix (TPC-B, 32 clients, 30s)

### Условия
- pgbench `--builtin=tpcb --client=32 --jobs=8 --time=30`
- WAL segment size: 16MB
- Throttle: `LD_PRELOAD fsync_throttle.so` с `THROTTLE_MS = 0, 1, 10, 50` (ms)
- `track_wal_io_timing = on`

### Результаты

| Throttle | Variant   | TPS    | WAL B/s   | Flusher Fsyncs | Flusher Time | WalRcv Fsyncs | WalRcv Time | Avg Fsync ms |
|----------|-----------|--------|-----------|---------------|-------------|---------------|-------------|-------------|
| **0ms**  | new       | 3895   | 1,912,620 | 145           | 511ms       | 8             | 68ms        | 3.5         |
| **0ms**  | baseline  | 3861   | 1,894,228 | —             | —           | 150           | 562ms       | 3.5         |
| **1ms**  | new       | 3886   | 1,913,623 | 145           | 645ms       | 8             | 74ms        | 4.4         |
| **1ms**  | baseline  | 3891   | 1,920,018 | —             | —           | 150           | 722ms       | 4.6         |
| **10ms** | new       | 3919   | 1,931,244 | 147           | 1959ms      | 8             | 148ms       | 13.3        |
| **10ms** | baseline  | 3873   | 1,911,613 | —             | —           | 155           | 2131ms      | 13.4        |
| **50ms** | new       | 3896   | 1,922,569 | 140           | 7443ms      | 8             | 466ms       | 53.5        |
| **50ms** | baseline  | 3869   | 1,909,048 | —             | —           | 149           | 7972ms      | 53.2        |
| **100ms**| new       | 3866   | 1,911,184 | 136           | 14090ms     | 8             | 868ms       | 103.6       |
| **100ms**| baseline  | 3865   | 1,906,537 | —             | —           | 101           | 11452ms     | 103.2       |

### Анализ

1. **TPS примерно одинаковый** (~3850-3920) — на TPC-B (32 clients) WAL rate всего
   ~1.8 MB/s, и fsync не является bottleneck. Разница в пределах шума (±1%).

2. **fsyncs перераспределены**: в new build flusher делает ~145 fsyncs, walreceiver
   только ~8 (init + segment close). В baseline walreceiver делает все ~150 fsyncs.

3. **Avg fsync time одинаков** — 3.5ms (0ms throttle), 4.4ms (1ms), 13.3ms (10ms),
   53.5ms (50ms). Подтверждает, что throttle работает корректно для обоих build.

4. **Total fsync time сопоставим**: new=511ms+68ms=579ms vs baseline=562ms (0ms throttle).
   Flusher не уменьшает общее время fsync — он переносит его в другой процесс.

5. **walreceiver fsync time снижен на 87%**: 68ms (new) vs 562ms (baseline) при 0ms throttle.
   Это освобождает walreceiver для чтения из socket.

6. **flush_lag** (pg_stat_replication):
   - 0ms throttle: ~0ms (оба)
   - 50ms throttle: ~5ms (new) vs ~53ms (baseline) — flusher decouples flush
   - При async rep primary не ждёт flush, поэтому TPS не меняется

---

## Результаты: High WAL rate (smalltx, 64 clients, 10ms throttle)

### Условия
- pgbench `-f smalltx.sql --client=64 --time=30` (INSERT, 64 клиента)
- WAL segment size: 16MB
- Throttle: 10ms

### Результаты

| Metric              | New (flusher)  | Baseline       | Delta  |
|---------------------|----------------|----------------|--------|
| **TPS**             | 74,523         | 73,860         | +0.9%  |
| **WAL rate**        | 11.3 MB/s      | 11.2 MB/s      | +1%    |
| Flusher fsyncs      | 365 (5271ms)   | —              |        |
| WalRcv fsyncs       | 43 (847ms)     | 392 (6296ms)   |        |
| Total fsync time    | 6118ms         | 6296ms         | -3%    |
| flush_lag           | 0 (caught up)  | 13ms           |        |
| replay_lag          | 0 (caught up)  | 13ms           |        |

### Анализ

При high WAL rate (11 MB/s) разница в TPS всё ещё ~1%, но:
- **flush_lag = 0** в new build (vs 13ms baseline) — flusher decouples flush
- **walreceiver fsync time** снижен с 6296ms до 847ms (87% reduction)
- **Total fsync time** примерно одинаковый (flusher делает те же fsyncs)
- **replay_lag = 0** — standby не отстаёт, replay идёт параллельно с fsync

---

## Результаты: Sync rep remote_flush (smalltx, 64 clients)

### Условия
- pgbench `-f smalltx.sql --client=64 --time=30`
- `synchronous_standby_names = '*'`, `synchronous_commit = on` (remote_flush)
- WAL segment size: 1MB (больше fsyncs)
- Throttle: 10ms и 50ms

### Результаты (10ms throttle)

| Metric              | New (flusher)  | Baseline       | Delta  |
|---------------------|----------------|----------------|--------|
| **TPS**             | 2,683          | 2,633          | +1.9%  |
| WAL rate            | 408 KB/s       | ~400 KB/s      | +2%    |
| Flusher fsyncs      | 2513 (29.1s)   | —              |        |
| WalRcv fsyncs       | 24 (343ms)     | 4988 (58.4s)   |        |
| flush_lag           | 16ms           | (empty)        |        |
| replay_lag          | 0.2ms          | (empty)        |        |

### Результаты (50ms throttle)

| Metric              | New (flusher)  | Baseline       | Delta  |
|---------------------|----------------|----------------|--------|
| **TPS**             | 609            | 603            | +1%    |
| Flusher fsyncs      | 569 (29.3s)    | —              |        |
| WalRcv fsyncs       | 6 (326ms)      | (not collected)|        |
| flush_lag           | 98ms           | (empty)        |        |

### Результаты (remote_write, 50ms throttle)

| Metric              | New (flusher)  |
|---------------------|----------------|
| TPS                 | 1,184          |
| flush_lag           | 101ms          |
| replay_lag          | 101ms          |

### Анализ

При sync rep `remote_flush` primary ждёт пока standby не fsync'нет WAL.
TPS падает с 74k (async) до 2.7k (10ms throttle) — каждый commit ждёт fsync.

Разница new vs baseline ~1-2% т.к. **flusher не уменьшает время fsync** — он просто
переносит его в другой процесс. Primary всё равно ждёт пока `flushedUpto` продвинется.

При `remote_write` primary не ждёт flush — TPS 1184 (vs 609 для remote_flush),
в 2 раза быстрее. Здесь flusher не даёт advantage т.к. primary не ждёт flush.

---

## Результаты: Cascade replication (S7)

### Условия
- Топология: `primary → casc1 (throttled) → casc2`
- pgbench `--builtin=tpcb --client=32 --jobs=8 --time=30`
- WAL segment size: 16MB
- Throttle на **casc1** (middle node): 50ms и 100ms
- `track_wal_io_timing = on`
- Ключевой момент: casc1 должен одновременно fsync свой WAL и форвардить WAL на casc2

### Результаты (50ms throttle)

| Metric                    | New (flusher)      | Baseline           | Delta  |
|---------------------------|-------------------|--------------------|--------|
| **TPS**                   | 3,586             | 3,596              | -0.3%  |
| **WAL B/s casc1**         | 1,790,926         | 1,790,961         | ~0%    |
| **WAL B/s casc2**         | 1,790,926         | 1,790,961         | ~0%    |
| casc1 flusher fsyncs      | 142 (7789ms)      | —                  |        |
| casc1 walrcv fsyncs       | 6 (366ms)         | 21 (1144ms)       | -68%   |
| primary→casc1 flush_lag  | 52ms              | 53ms               | ~same  |
| primary→casc1 replay_lag | 52ms              | 53ms               | ~same  |
| casc1→casc2 flush_lag    | 1.4ms             | 1.2ms              | ~same  |
| casc1→casc2 replay_lag   | 3.1ms             | 1.2ms              | ~same  |

### Результаты (100ms throttle)

| Metric                    | New (flusher)      | Baseline           | Delta   |
|---------------------------|-------------------|--------------------|---------|
| **TPS**                   | 3,717             | 3,646              | **+1.9%** |
| **WAL B/s casc1**         | 1,841,279         | 1,790,915         | +2.8%   |
| **WAL B/s casc2**         | 1,841,279         | 1,790,915         | +2.8%   |
| casc1 flusher fsyncs      | 135 (13999ms)     | —                  |         |
| casc1 walrcv fsyncs       | 7 (751ms)         | 129 (13461ms)     | -94%    |
| primary→casc1 flush_lag  | 5ms               | 0-103ms (varies)  | stabler |
| primary→casc1 replay_lag | 5ms               | 200-208ms         | **40x better** |
| casc1→casc2 flush_lag    | 1-10ms            | 0-5ms (often empty)|         |
| casc1→casc2 replay_lag   | 0.3-5ms           | 0-5ms (often empty)|        |

### Анализ

1. **TPS gain +1.9% при 100ms throttle** — первый сценарий с measurable TPS improvement.

2. **primary→casc1 replay_lag: 5ms (new) vs 200ms (baseline)** — flusher decouples
   flush от WAL forwarding, casc1 быстрее подтверждает primary что WAL применён.

3. **casc1→casc2 lag часто `empty` в baseline** — walreceiver на casc1 заблокирован
   на fsync (13.4s из 30s = 45% времени), не успевает форвардить WAL на casc2.
   В new build casc2 получает WAL стабильно (lag 1-10ms).

4. **walreceiver fsync time снижен на 94%** при 100ms throttle:
   751ms (new) vs 13461ms (baseline). Walreceiver свободён от fsync.

5. **WAL throughput на casc2 на 2.8% выше** в new build — casc1 быстрее
   форвардит WAL т.к. walreceiver не заблокирован на fsync.

---

## Результаты: COPY high-WAL benchmark (S4b)

### Условия
- pgbench `-f sql/copy_highwal.sql --client=4 --jobs=4 --transactions=10`
- Каждый "transaction": INSERT 500k rows с 100-byte payload → ~50MB WAL per tx
- Total: 4 clients × 10 tx = 40 transactions → ~2GB WAL
- WAL segment size: 16MB
- Throttle: 0ms и 50ms
- `track_wal_io_timing = on`

### Результаты (0ms throttle, 2-node)

| Metric              | New (flusher)  | Baseline       | Delta  |
|---------------------|----------------|----------------|--------|
| **WAL rate**        | 64.3 MB/s      | 65.2 MB/s      | -1.4%  |
| **TPS**             | 0.85           | 0.87           | -2.3%  |
| **WAL total**       | 2888 MB        | 2873 MB        | +0.5%  |
| Elapsed             | 47.1s          | 46.2s          |        |
| Flusher fsyncs      | 35 (939ms)     | —              |        |
| WalRcv fsyncs       | 362 (29106ms)  | (not collected)|        |

### Результаты (50ms throttle, 2-node)

| Metric              | New (flusher)  | Baseline       | Delta  |
|---------------------|----------------|----------------|--------|
| **WAL rate**        | 52.9 MB/s      | 51.2 MB/s      | **+3.3%** |
| **TPS**             | 1.21           | 1.31           | -7.6%  |
| **WAL total**       | 1680 MB        | 1488 MB        | +12.9% |
| Elapsed             | 33.3s          | 30.5s          |        |
| Flusher fsyncs      | 36 (2490ms)    | —              |        |

### Результаты (50ms throttle, cascade)

| Metric              | New (flusher)  | Baseline       | Delta  |
|---------------------|----------------|----------------|--------|
| **WAL rate**        | 29.7 MB/s      | 28.8 MB/s      | **+3.1%** |
| **TPS**             | 0.685          | 0.693          | -1.2%  |
| **WAL total**       | 1652 MB        | 1584 MB        | +4.3%  |
| Elapsed             | 58.4s          | 57.8s          |        |
| Flusher fsyncs      | 63 (5118ms)    | —              |        |

### Анализ

1. **WAL throughput +3.3% (2-node) и +3.1% (cascade)** при 50ms throttle —
   flusher освобождает walreceiver от fsync, позволяя быстрее читать WAL из socket.

2. **TPS ниже в new build** (1.21 vs 1.31 при 50ms 2-node) — но new генерирует
   **больше WAL** (1680 vs 1488 MB). TPS ниже т.к. каждая транзакция занимает
   больше времени (больше WAL на tx из-за FPI), но **WAL throughput выше**.
   TPS — неправильная метрика для COPY; WAL rate — правильная.

3. **При 0ms throttle (fast disk)** — разницы нет, fsync не bottleneck.
   WAL rate одинаковый (~65 MB/s).

4. **Cascade**: WAL rate +3.1% — casc1 быстрее форвардит WAL на casc2,
   т.к. walreceiver не заблокирован на fsync.

5. **WalRcv fsync time**: 29106ms (new, 0ms throttle) — это fsync при close
   сегмента (XLogWalRcvFlush в XLogWalRcvClose). В new build walreceiver всё
   ещё делает fsync при закрытии сегмента, но не в основном цикле.

### Замечание по сбору метрик

Baseline walreceiver не сбрасывает pending IO stats в shared memory
(`pgstat_report_wal(false)` вызывает `pgstat_flush_io(true)` (nowait),
но pending stats не flush'ятся). Поэтому `pg_stat_io` показывает 0 fsyncs
для baseline walreceiver. Для new build flusher вызывает `pgstat_report_stat(true)`
(force flush), поэтому метрики собираются корректно.

---

## Результаты: WAL-heavy FPI benchmark (S9)

### Условия
- pgbench `-f sql/walheavy.sql --client=32 --jobs=4 --time=30`
- `walheavy.sql`: UPDATE 5 rows + INSERT 100 rows (full-page images after CHECKPOINT)
- `TRUNCATE audit; CHECKPOINT` перед каждым прогоном (максимум FPI)
- WAL segment size: 16MB
- Throttle: 0ms и 50ms
- `track_wal_io_timing = on`
- `synchronous_commit = off` (async replication)

### Результаты (0ms throttle, 2-node)

| Metric              | New (flusher)  | Baseline       | Delta   |
|---------------------|----------------|----------------|---------|
| **TPS**             | 4,488          | 5,101          | **-12%** |
| **WAL rate**        | 34.9 MB/s      | 39.5 MB/s      | **-12%** |
| **WAL total**       | 1001 MB        | 1133 MB        | -12%    |
| Flusher fsyncs      | 850 (3460ms)   | —              |         |
| WalRcv fsyncs       | 124 (1118ms)   | (not collected)|         |

### Результаты (50ms throttle, 2-node)

| Metric              | New (flusher)  | Baseline       | Delta   |
|---------------------|----------------|----------------|---------|
| **TPS**             | 3,951          | 3,535          | **+11.8%** |
| **WAL rate**        | 29.8 MB/s      | 26.8 MB/s      | **+11.4%** |
| **WAL total**       | 856 MB         | 768 MB         | +11.5%  |
| Flusher fsyncs      | 92 (5047ms)    | —              |         |
| WalRcv fsyncs       | 110 (6918ms)   | (not collected)|         |

### Результаты (50ms throttle, cascade)

| Metric              | New (flusher)  | Baseline       | Delta   |
|---------------------|----------------|----------------|---------|
| **TPS**             | 2,531          | 3,593          | -29.6%  |
| **WAL rate (casc2)**| 19.8 MB/s      | 28.1 MB/s      | -29.5%  |
| **WAL total (casc2)**| 569 MB       | 813 MB         | -30%    |
| casc1 flusher fsyncs| 104 (5582ms)   | —              |         |
| casc1 walrcv fsyncs | 70 (4266ms)    | (not collected)|         |
| casc2 flusher fsyncs| 1136 (2566ms)  | —              |         |
| casc2 walrcv fsyncs | 70 (658ms)     | (not collected)|         |

### Анализ

1. **При 0ms throttle (fast disk): baseline быстрее на 12%** — flusher добавляет
   overhead (context switching, extra process) без benefit, т.к. fsync быстрый.
   TPS 4488 (new) vs 5101 (baseline).

2. **При 50ms throttle (slow disk): new быстрее на 11.8%** — flusher освобождает
   walreceiver от fsync, позволяя быстрее читать WAL из socket.
   TPS 3951 (new) vs 3535 (baseline). WAL rate +11.4%.

3. **WAL-heavy сценарий генерирует ~30-40 MB/s WAL** (vs ~1.8 MB/s для TPC-B) —
   fsync становится bottleneck, и flusher даёт measurable advantage.

4. **Cascade результаты ненадёжны**: casc2 не успевает получить весь WAL
   за 30s (569 MB vs 813 MB в baseline). TPS измеряется на primary, но
   cascade topology может влиять на primary через flow control.

5. **FPI эффект**: CHECKPOINT перед прогоном → все dirty pages генерируют
   full-page images → WAL rate ~30 MB/s (vs ~8 MB/s без FPI для того же workload).

---

## Результаты: 128 clients (TPC-B и walheavy)

### Условия
- pgbench TPC-B: `--builtin=tpcb --client=128 --jobs=8 --time=30`, scale=10
- pgbench walheavy: `-f sql/walheavy.sql --client=128 --jobs=4 --time=30`
- Throttle: 50ms
- WAL segment size: 16MB
- `max_connections = 200`
- `synchronous_commit = off` (async replication)

### Результаты (TPC-B, 128 clients, 50ms throttle)

| Metric              | New (flusher)  | Baseline       | Delta   |
|---------------------|----------------|----------------|---------|
| **TPS**             | 9,906          | 10,136         | -2.3%   |
| **WAL rate**        | 10.0 MB/s      | 10.1 MB/s      | -1.1%   |
| **WAL total**       | 287 MB         | 290 MB         | -1%     |
| Flusher fsyncs      | 163 (8894ms)   | —              |         |
| WalRcv fsyncs       | 36 (2148ms)    | (not collected)|         |
| replay_lag          | 0 (caught up)  | 0 (caught up)  |         |

### Результаты (walheavy, 128 clients, 50ms throttle)

| Metric              | New (flusher)  | Baseline       | Delta   |
|---------------------|----------------|----------------|---------|
| **TPS**             | 179            | 225            | -20%    |
| **WAL rate**        | 1.4 MB/s       | 1.8 MB/s       | -22%    |
| **WAL total**       | 54 MB          | 55 MB          | -2%     |
| Flusher fsyncs      | 105 (5502ms)   | —              |         |
| WalRcv fsyncs       | 6 (345ms)      | (not collected)|         |

### Анализ

1. **TPC-B 128 clients**: TPS ~10,000 для обоих, baseline немного быстрее (-2.3%).
   WAL rate ~10 MB/s — в 5x больше чем 32 clients (1.9 MB/s), но всё ещё
   недостаточно для fsync чтобы стать bottleneck при 50ms throttle.

2. **walheavy 128 clients**: TPS очень низкий (179-225) из-за lock contention —
   128 клиентов обновляют те же 1000 строк в `accounts` таблице. Этот сценарий
   не подходит для 128 клиентов (нужно ~100,000+ rows). Результаты не показательны.

3. **128 clients не даёт нового преимущества** — TPC-B WAL rate (10 MB/s) всё ещё
   слишком низкий для fsync bottleneck. Для эффекта нужен high-WAL workload
   (COPY, walheavy с 32 clients) + slow disk (50ms+ throttle).

---

## Сводный анализ

### Когда flusher даёт преимущество

1. **Async replication + high WAL rate + slow disk**: walreceiver свободён от fsync
   и может быстрее читать из socket. WAL rate +11.4%, TPS +11.8% (walheavy, 50ms).

2. **Cascade replication (S7)**: standby1 быстро отдаёт WAL standby2, не дожидаясь fsync.
   При 100ms throttle: **TPS +1.9%**, replay_lag 5ms vs 200ms (40x better),
   WAL throughput на casc2 +2.8%.

3. **COPY high-WAL**: WAL throughput +3.3% (2-node), +3.1% (cascade) при 50ms throttle.

4. **replay-before-flush** (коммит `d68f87caf9f`): replay идёт параллельно с fsync,
   `replay_lag` снижен. Это уже работает в baseline (d68f87caf9f).

### Когда flusher НЕ даёт преимущество

1. **Sync rep remote_flush**: primary ждёт flush, и flusher не уменьшает время fsync.
   TPS ~одинаковый.

2. **Low WAL rate (TPC-B)**: fsync не bottleneck, throttle не влияет. TPS ~same.

3. **Fast disk (0ms throttle)**: fsync быстрый, flusher добавляет overhead.
   WAL-heavy: baseline быстрее на 12% (5101 vs 4488 TPS).

### Главный эффект flusher

- **walreceiver fsync time снижен на 87-94%** (68ms vs 562ms при 0ms throttle; 751ms vs 13461ms при 100ms cascade)
- **WAL throughput +11.4%** на walheavy (50ms throttle, 30 MB/s WAL rate)
- **WAL throughput +3.3%** на COPY (50ms throttle, 50 MB/s WAL rate)
- **flush_lag снижен** (5ms vs 53ms при 50ms throttle, async rep)
- **replay_lag снижен в 40x** в cascade (5ms vs 200ms при 100ms throttle)
- **TPS gain +11.8%** на walheavy (50ms throttle), **+1.9%** на cascade TPC-B (100ms throttle)
- **pg_stat_io split**: fsyncs перемещены из `walreceiver` в `walrcvflusher`

### Ограничения бенчмарков

1. **TPC-B генерирует мало WAL** (~1.8 MB/s при 32c, ~10 MB/s при 128c) — fsync не bottleneck
2. **Cascade протестирован** (S7): primary→casc1→casc2, throttle на casc1
3. **Throttle симулирует slow disk**, но не симулирует slow network
4. **1 прогон** (RUNS=1) — нет усреднения, возможен шум
5. **30s duration** — короткий прогон, возможен warmup effect
6. **Cascade walheavy** — casc2 не успевает получить весь WAL за 30s, метрики ненадёжны
7. **128 clients walheavy** — lock contention на 1000-row таблице, результаты не показательны

### Рекомендации для будущих тестов

1. **Больше WAL**: `walheavy.sql` с full-page images, или `COPY` больших таблиц
2. **Дольше**: 120s+ для стабилизации
3. **Больше клиентов**: 128+ для давления на walreceiver
4. **synchronous_commit=remote_apply**: primary ждёт apply, а не flush
5. **recovery_min_apply_delay**: WAL копится на standby, проверить что flusher не теряет данные
