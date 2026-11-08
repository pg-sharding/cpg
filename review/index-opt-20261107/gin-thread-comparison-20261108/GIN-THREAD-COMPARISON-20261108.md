# GIN: сравнение с тредом David Geier и нашей историей

Проверено 2026-11-08. **Для нынешних G1 (`gin-advance-v3`) и G2
(`gin-lazy-v4`) прямого дубликата в указанном треде нет. Для прежних наших
pg_trgm sorting/radix/adaptive/MSD экспериментов пересечение прямое: это
именно исходная серия, поверх которой надо описывать наши followups.**
Отсутствие найденного дубликата в этом ограниченном обзоре не доказывает
новизну G1/G2 во всей литературе или рассылке.

Ссылка ведёт на [Reduce build times of pg_trgm GIN indexes](https://www.postgresql.org/message-id/5d366878-2007-4d31-861e-19294b7a583b%40gmail.com),
начатый David Geier 2026-01-05. Проверены 52 сообщения и все 59 вложений
архивного topic 53025, версии v1–v11, и два более свежих публичных ответа
2026-11-05. Отдельно проверено продолжение [Use correct collation in pg_trgm](https://www.postgresql.org/message-id/db087c3e-230e-4119-8a03-8b5d74956bc2%40gmail.com):
21 сообщение / 15 вложений, до v8 от 2026-10-23. Вложения Base64 декодированы
локально **как данные**; их C/SQL/patch-код не запускался и не применялся.
Полные почтовые тела и скачанные upstream patches в публичный результат не входят.

## Какие механизмы реально сравниваются

| Вариант | Представление и операция | Основной участок | Уровень пропуска / экономии |
|---|---|---|---|
| Geier, extraction/sorting | Сначала полученные из одного значения trigrams/Datums; сортировка и dedup | `generate_trgm`, `generate_wildcard_trgm`, `ginExtractEntries` | Сравнения/перестановки ключей, подготовка поиска и индексируемых значений |
| Geier v11-0003 | Временный build/pending-cleanup accumulator: `(attnum, category, Datum)` → массив TID | `ginInsertBAEntry`, `ginInsertBAEntries`, `ginBeginBAScan`, `ginGetBAEntry` в `ginbulk.c` | Поиск ключа через simplehash вместо RB-tree; последующая сортировка distinct keys и TID-массивов |
| G1, наш advance v3 | Уже **отсортированный, декодированный** массив `ItemPointerData` в scan entry | `ginAdvanceDecoded` и два decoded-list пути `entryGetItem` в `ginget.c` | Найти первый TID строго **больше** `advancePast`: два дешёвых линейных шага, затем exponential probe + binary upper bound |
| G2, наш lazy v4 | Приватная копия **сжатого суффикса posting-tree страницы**, затем один нужный segment | `entryCopyPostingPage`, `entryLoadNextSegment`, `entryLoadMoreItems`, exhaustion path `entryGetItem` | Не декодировать весь оставшийся page suffix заранее; обходить segment headers и декодировать по потребности |

Последний доступный [v11 от 2026-10-23](https://www.postgresql.org/message-id/25e5a1da-44c9-427a-b9f9-65aac16d9a30%40gmail.com)
содержит три независимых части: [integer comparators](https://www.postgresql.org/message-id/attachment/207171/v11-0001-Use-branchless-comparisons-in-btint4cmp-and-btin.patch),
[trigram radix+unique](https://www.postgresql.org/message-id/attachment/207172/v11-0002-Use-radix-sort-to-extract-trigrams.patch),
[hash accumulator](https://www.postgresql.org/message-id/attachment/207173/v11-0003-Replace-GIN-build-accumulator-RB-tree-with-a-has.patch).
Даты format-patch author/header (например, 2025-11 у comparator/radix)
не являются датами отправки: последняя публикация этих v11 — 2026-10-23.
Оба вида metadata сохранены отдельно. Ни одна из всех 59 просмотренных
версий/вложений основного треда не меняет
`ginget.c` или `ginscan.c`. Это проверка патчей и их функций, а не вывод из
одного пустого поиска по заголовку.

У v11-0003 действительно есть массивы TID и `ginCompareItemPointers`, но они
**сортируются при накоплении**, а не пересекаются/пропускаются при чтении.
Общий comparator — уже существующий primitive, не одинаковый алгоритм.
Встречающийся в его diff `GinSegmentInfo` находится в контексте typedefs.list;
это не добавление posting-segment decoder или lazy scan.

## G1: точное отличие и семантический контракт

G1 не извлекает trigrams, не сортирует входной массив и не заменяет accumulator.
Он ускоряет переход к уже заданному `advancePast` внутри двух decoded-list
веток `entryGetItem`. Переход — upper_bound: все `<= advancePast` пропускаются,
первый `>` передаётся прежней логике. `curItem` при исчерпании должен сохранять
последний TID для решения о следующей странице. Важны существующий порядок
6-byte TID/LOSSY sentinel, offsets, empty/end transitions и то, что вызовы
`dropItem`/RNG сохраняются для тех же eligible items, а не для отброшенного
префикса. Отдельный bitmap-offset путь этим патчем не оптимизируется.

В pinned master `ginCompareItemPointers` собирает логический block/offset в
unsigned 64-bit значения и вызывает `pg_cmp_u64`; это не fmgr-вызов `btint8cmp`
и не новое сравнение raw восьми байтов `ItemPointerData`. Поэтому comparator
часть Geier не реализует G1 косвенно. Наша собственная версия v1 была отвергнута,
а её failure/regression evidence остаётся историей, не доказательством нового
алгоритма. Галопирующий поиск/upper_bound сами по себе общеизвестны.

G1 native module содержит извлечённый `entryGetItem`/search body с моделью
refill и тем же comparator. Это micro потребления списка. Вложения Geier
содержат build/trigram sorting, а не такой kernel. Micro не покрывает реальные
buffer locks, декодирование, visibility и concurrent SQL; его результаты нельзя
сравнивать с CREATE INDEX или выдавать за суммируемые с ними ускорения.

## G2: что уже умел master и что добавляет lazy decode

В baseline `GinDataLeafPageGetItems` **уже** умеет пройти segment headers до
сегмента, следующая граница которого больше `advancePast`, а затем вызывает
`ginPostingListDecodeAllSegments` для выбранного суффикса. Следовательно,
формулировка «мы впервые научили GIN пропускать compressed segments» неверна.
Наш вклад уже: отложить декодирование неиспользованного остатка после этого
выбора. Первая posting-tree page остаётся eager ради frequency estimate;
sequential/eager и pre-9.4 fallback сохраняются, а streaming-потребитель может
перейти к eager decoding оставшейся приватной копии.

Сжатые bytes копируются под существующим lock в собственную память. После
unlock нельзя хранить указатель в изменяемую shared page. Последний segment
нужно декодировать даже при пустом результате, чтобы сохранить last TID для
page transition. Неизменны порядок `advancePast`, page/rightlink protocol,
нормальный pin и cleanup/rescan/free private snapshot. V4 по сравнению с V3
переносит проверку `postingData` в exhaustion path, а не вводит новый codec.

G2 native module извлекает scan/refill/segment bodies и codec, моделирует page
storage/lock/refill и считает реальные decode/snapshot действия. Это не
`ginInsertBAEntry`. Сохранённый dispatch erratum и full-read negatives нельзя
потерять при разговоре о prior art: совпадение маленького kernel/primitive
не делает benchmark полным AM, и разные dispatch paths не дают честный control.

## Почему «там только build, у нас SELECT» слишком грубо

У [trigram radix patch](https://www.postgresql.org/message-id/attachment/207172/v11-0002-Use-radix-sort-to-extract-trigrams.patch)
оба call sites — `generate_trgm` и `generate_wildcard_trgm`. В pinned
`trgm_gin.c` они используются и в `gin_extract_query_trgm`: query extraction
тоже может измениться. Это upstream стадия того же SELECT, но не наша
posting-list advance/decode стадия. Аналогично source call graph показывает
`ginInsertBAEntries` не только в `gininsert.c` build, но и в `ginfast.c` при
pending-list cleanup. Поэтому назвать hash accumulator исключительно
CREATE INDEX кодом тоже неточно. [Описание автора accumulator](https://www.postgresql.org/message-id/10395cb6-a804-49ac-b2f1-3f98d7204359%40gmail.com)
подтверждает его стратегию и отмечает изменение memory accounting/размера
индекса; из этого не следует изменение posting-list формата.

Это общие execution pipelines и общий объект GIN, но **не прямое совпадение
реализаций**. Совместный выигрыш не измерялся. Разные накопления/flush batches
могут дать другую физическую форму дерева/границы сегментов; одинаковый format
не означает byte-identical index и те же scan costs.

## Текстовые конфликты и возможность совместить

- С G1 ни один из трёх последних v11 patches не имеет общего изменённого файла.
- С G2 общий только `src/include/access/gin_private.h` у accumulator patch:
  Geier меняет `BuildAccumulator`/удаляет `GinEntryAccumulator` и RB include;
  G2 добавляет три private scan fields в `GinScanEntryData`. Структуры и hunk
  области различны. Это ожидаемо совместимые изменения, **не выполненная
  совместная apply/build/SQL проверка** и не обещание будущего conflict-free rebase.
- G1 и G2 между собой меняют соседние/общие участки `entryGetItem`. Их нельзя
  молча приложить как готовую последовательную серию: нужен осознанный merge
  exhaustion/refill path, строгого upper_bound и `curItem`. Новый linear scan
  внутри G2 segment refill также не автоматически заменяется G1 helper.

Для будущего объединения разумна матрица master / Geier-only / G1-only / G2-only
/ combined. Сначала одинаковый физический seed для изоляции reader, отдельно
создание индекса каждым builder для end-to-end эффекта. Нужны все ответы,
selective AND, OR/dense sequential, absent, short lists, NULL/lossy/fuzzy,
pending cleanup, mutation/rescan/concurrency, codec boundaries и negatives.
Это план будущей проверки, не новый выполненный benchmark этой заметки.

## Что уже закоммичено и входит в наш baseline

Проверены local Git ancestry к `72b9498df9a369e747f8d96efb5a6cd33c2451e2`
и primary mail/доступные official mirror sources:

| Commit | Дата | Уже у нас в baseline |
|---|---|---|
| `bba81f9d3d4f512280bd55751a450dac6f02d406` | 2026-01-09 | inline `ginCompareAttEntries` |
| `6f5ad00ab763f9e029ec591f7f650bd09c1e933f` | 2026-04-07 | NULL extraction + templated sort/dedup `ginExtractEntries` |
| `9f3755ea07aa8858999bdac3d33151e93d2643e2` | 2026-04-07 | pg_trgm templated qsort и equality-only qunique comparator |
| `41467b1d88303fbaea4ddd20c21ac4b8ce6b92d7` | 2026-11-05 | branchless `btint4cmp` / `btint8cmp` |

[Письмо о первых April commits](https://www.postgresql.org/message-id/6439c655-e281-409d-b884-6586750d5820%40iki.fi),
[November commit notice](https://www.postgresql.org/message-id/df6a9bed-14b1-4540-b88d-0f3f47b3e9c3%40iki.fi)
и [official branchless commit](https://github.com/postgres/postgres/commit/41467b1d88303fbaea4ddd20c21ac4b8ce6b92d7)
согласуются с Git. Нельзя считать эти уже включённые изменения новым ускорением
G1/G2 или нашей typed-only работы. В соответствующих commit credits есть Kirill
Reshke; это дополнительно связывает раннюю историю с тем же обсуждением.

[CommitFest 6418](https://commitfest.postgresql.org/patch/6418/) при проверке
показывал target 20, Ready for Committer, три v11 patches и последний ответ
2026-11-05. Это статус всей записи, не доказательство, что каждый её patch
закоммичен: comparator уже merged, остальное надо разделять. Полученные
[official master ginbulk.c](https://raw.githubusercontent.com/postgres/postgres/master/src/backend/access/gin/ginbulk.c)
и [trgm_op.c](https://raw.githubusercontent.com/postgres/postgres/master/contrib/pg_trgm/trgm_op.c)
ещё содержат RB-tree и templated qsort соответственно. Это проверенные снимки,
а не обещание неизменного статуса будущего master; web cache имеет свою дату.

## Где пересечение прямое: наши старые pg_trgm эксперименты

Для bitmap bucket occupancy / меньшего radix / in-place MSD / adaptive small
sort это **followups к тому же sort**, а не отдельная новая идея GIN.
[14 сентября](https://www.postgresql.org/message-id/10afd923-38f4-451c-af89-34f8654533cb%40googlemail.com)
автор уже прикладывал in-place MSD и сообщил отрицательный результат, обсуждал
память и объединение unique/copy. [5 ноября](https://www.postgresql.org/message-id/2cb613f1-37d7-4283-b2ad-3afff466134c%40iki.fi)
Heikki отдельно указал регрессию очень маленьких trigram arrays и предложил
сохранять прежний qsort для них. Наш конкретный codegen/threshold/профиль и
дополнительные measurements могут быть полезным вкладом, но общий adaptive
fallback, radix или MSD нельзя выдавать за не предлагавшийся алгоритм.

Collation offshoot [latest v8](https://www.postgresql.org/message-id/28dcdcfe-a8e2-4619-8514-a0216715d510%40gmail.com)
меняет casing/word-boundary extraction и её collation propagation. Все 15
просмотренных вложений остаются вне GIN posting consumer: это не lazy snapshot
и не decoded TID search. При объединении с pg_trgm reader tests нужны collation
и exact-match reference answers, а не предположение, что extraction нейтральна.
Статус всей collation серии отдельно здесь не объявляется.

## Как описывать наши дальнейшие письма

Для G1: «decoded posting-list advance in `entryGetItem`, preserving strict
`advancePast` and existing RNG/page-transition semantics». Для G2: «on-demand
decoding of a privately owned compressed posting-page suffix, after existing
segment selection; first-page and sequential eager paths retained».
Сослаться на Geier как related GIN performance work и явно отделить extraction/
accumulation от consumption. Указывать, что соответствующие ранние commits
уже входят в baseline. Не писать «first galloping GIN», «first segment skipping»,
«all GIN prior art checked» или складывать авторские CREATE INDEX проценты с
нашими scan цифрами. Будущий [UNSENT addendum](email-addendum-UNSENT.txt) сохранён
отдельно: ни один frozen source/draft/bundle не переписан.

## Доказательная база и ограничения поиска

[attachment-index.json](attachment-index.json) содержит все 59 filename/date/FK/
Base64 decode SHA и изменённые paths; [message-index.json](message-index.json)
содержит 52 записи без тел. [collation-offshoot-index.json](collation-offshoot-index.json)
покрывает продолжение. [source-and-status-audit.json](source-and-status-audit.json)
фиксирует наши точные diffs/native inputs, pinned source function references,
четыре Git ancestry checks и shared-file matrix. [search-audit.json](search-audit.json)
фиксирует bounds/READ ONLY/источники и исключения.

Архивная копия достигает 2026-10-23, поэтому November followups и актуальная CF
проверены через web. По reply-links вне topic прямых продолжений не найдено,
но отдельный collation thread найден по явной ссылке, а не объявлен отсутствующим.
Это не глобальный proof of novelty; другие posting-list/search/compression
работы и старые GIN discussions требуют самостоятельного prior-art review.
Ни VM158/84, ни builds/core/native/SQL timings этой задачей не использовались.
