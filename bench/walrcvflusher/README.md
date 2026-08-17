# walrcvflusher benchmarks

Бенчмарки для коммита `69cf50b2dac` ("Flush async"), добавляющего процесс `walrcvflusher`,
который выносит `fsync` WAL из `walreceiver` в отдельный процесс при потоковой репликации.

## Структура

```
bench/walrcvflusher/
├── scripts/
│   ├── common.sh          # общие переменные, хелперы (source из всех скриптов)
│   ├── setup.sh           # инициализация primary + standby
│   ├── cascade_setup.sh   # инициализация 3-уровневого каскада
│   ├── run_bench.sh       # один прогон: warmup → pgbench → сбор метрик
│   ├── collect_metrics.sh # автономный сбор метрик (pg_stat_io, wait events, lag)
│   ├── matrix.sh          # оркестратор всех сценариев S0-S11
│   ├── compare.sh         # сравнение baseline vs new
│   └── fsync_throttle.c   # LD_PRELOAD библиотека для замедления fsync
├── sql/
│   ├── smalltx.sql        # S3: малые транзакции, высокий WAL rate
│   ├── copy_bulk.sql      # S4: большие транзакции (bulk INSERT)
│   ├── walheavy.sql       # S9: UPDATE + INSERT (full-page images)
│   └── prepare_tables.sql # создание таблиц для кастомных скриптов
└── results/               # результаты прогонов (создаётся автоматически)
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

### 4. Запуск всех сценариев (new build)

```bash
./scripts/matrix.sh new
```

### 5. Пересборка baseline и прогон

```bash
# Пересобрать без flusher (HEAD~1 = d68f87caf9f, уже с replay-before-flush)
git checkout d68f87caf9f
make -j install

# Пересоздать кластер (тот же конфиг, другой бинарник)
./scripts/setup.sh

# Прогнать те же сценарии
./scripts/matrix.sh baseline
```

### 6. Сравнение

```bash
./scripts/compare.sh
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
       round(fsyncs_time / greatest(fsyncs,1), 3) AS avg_fsync_ms
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

## S7: Каскадная репликация

```bash
# Отдельная инициализация 3 узлов
./scripts/cascade_setup.sh

# Прогон (использует CASC1_PORT, CASC2_PORT)
./scripts/run_bench.sh "${VARIANT}_S7_cascade" --builtin=tpcb --client=32 --jobs=8

# Сбор lag на обоих уровнях
psql -p 55432 -c "SELECT application_name, write_lag, flush_lag, replay_lag FROM pg_stat_replication"
psql -p 55434 -c "SELECT application_name, write_lag, flush_lag, replay_lag FROM pg_stat_replication"
```

## S10: Изоляция вклада коммитов

Коммит `d68f87caf9f` ("replay before flush") + `69cf50b2dac` ("flusher process") —
два независимых изменения. Для разделения вклада:

```bash
# 1. До обоих коммитов
git checkout d68f87caf9f~1 && make -j install && ./scripts/setup.sh && ./scripts/matrix.sh pre_d68 S0

# 2. Только replay-before-flush (без flusher)
git checkout d68f87caf9f && make -j install && ./scripts/setup.sh && ./scripts/matrix.sh d68 S0

# 3. + Flusher process
git checkout 69cf50b2dac && make -j install && ./scripts/setup.sh && ./scripts/matrix.sh new S0
```

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
