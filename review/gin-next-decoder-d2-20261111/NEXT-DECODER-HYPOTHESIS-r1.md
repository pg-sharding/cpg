# Следующая decoder-гипотеза после D2: сначала доказать изменение ASM

Read-only анализ 2026-11-11. Никакого D3 кода, builds, VM-команд или timings этой запиской не создано. Frozen inputs/results и source refs не менялись.

**Refactor «прочитать byte0 один раз» сам по себе не является доказанным следующим performance fix.** В C source D2 ранний guard и старый `decode_varbyte` действительно описывают проверку первого байта дважды, но actual normal ASM уже переиспользует прочитанный byte0 и сразу переходит к продолжению. Не следует запускать source-only перестановку как обязательный ремонт якобы установленной двойной инструкции.

По сообщению root, независимый аудит D2 результатов прошёл: dense128 CPU −10.71/−10.80% к B, но delta2 +4.52/+5.12%, delta3 +7.40/+6.81%, delta4 +6.21/+5.49%; skew1000 whole100-probe SQL −2.81/−2.46%, остальные SQL смешанные. Здесь эти результаты не пересчитывались; они задают вопрос о сохранённой multibyte цене, **не её причину**.

## Что показывает фактический normal ASM

В [D2-guard-selected.txt](normal-asm-review-r1/D2-guard-selected.txt):

- `0x293` загружает byte0;
- `0x2a2/0x2a4` проверяет его continuation bit и при установленном бите переходит на `0x320`;
- `0x320` сразу читает byte1, а `0x325..0x337` использует уже загруженный byte0, mask0x7f и сдвиг следующего байта;
- `0x33a` проверяет continuation bit **byte1**, не byte0.

Таким образом, показанная multibyte ветка уже не содержит повторной загрузки/проверки byte0. Это не miscompile и не свидетельство лишней динамической проверки первого байта. [Root normal ASM review](normal-asm-review-r1/README.md) также показывает одинаковый frame B/D1/D2:6 saved registers +24 explicit RSP bytes. Spans592/864/848 включают alignment до следующего символа, поэтому не являются точными function sizes. По ним нельзя приписать остаточные4–7% instruction cache, branch predictor, allocator или register pressure.

## Допустимый source-contract возможного D3

В D2 commit `a85a9242f455b12c93528f3ace33eb69b6cd1008` `decode_varbyte` — static helper с единственным caller в `ginPostingListDecodeAllSegments`; read-only `git grep` по src нашёл только определение и этот вызов. Поэтому интерфейс можно было бы локально изменить, не создавая общий codec API. Если такой refactor понадобится для отдельного layout/codegen опыта, контракт должен быть следующим:

1. Сохраняется прежний `while (ptr < endptr)` и обычный output-growth check до декодирования очередной дельты. После него есть хотя бы один output slot. Только затем byte0 загружается и input pointer продвигается ровно на один байт.
2. При byte0 с continuation bit helper получает **значение уже потреблённого byte0** и pointer на byte1. Он инициализирует delta младшими7 bits byte0, читает следующие bytes с прежними shifts7/14/21/28/35/42 и возвращает **delta**, не cumulative TID. Caller прибавляет delta один раз. Нельзя повторно читать `ptr[-1]` или вызывать старый helper с pointer уже на byte1.
3. Все сдвигаемые значения должны оставаться uint64. Последний, седьмой байт сохраняет прежнее ограничение/Assert об отсутствии continuation bit. Обновлённый pointer должен указывать на первый byte следующей дельты, как у старого helper.
4. При однобайтовом byte0 попытка batch относится к **ещё трём** bytes: после потребления первого нужны `endptr - ptr >= 3` и четыре свободных output slots, включая ещё не выданный первый. Эти bounds проверяются до чтения остальных трёх bytes. Все их high bits должны быть clear. Положительный путь выдаёт четыре последовательных cumulative TID; отрицательный выдаёт только первый и оставляет последующие bytes нетронутыми. Если первым TID уже записан, эквивалентный capacity check относится к трём оставшимся slots; смешивать эти две конвенции нельзя.
5. First item каждого segment по-прежнему хранится явно и не проходит через этот loop. Input не пересекает `segment->nbytes`, включая padding. При недостатке четырёх slots нельзя заранее увеличивать output capacity ради batch: один scalar output и последующий прежний growth сохраняют allocation policy. Format, segment traversal, NULL `ndecoded_out`, allocation calls и materialization остаются прежними.

Старый codec рассчитан на valid internal posting lists; helper без end pointer не становится валидатором повреждённых входов. Записка не обещает новый corruption/malformed-input контракт. Строгое сохранение прежней valid-input семантики — отдельное обязательство, даже если generated ASM останется прежним.

## Более предметный следующий возможный опыт

**Scalar fallthrough против отдельного batch block/helper и размещения кода**, только если получится содержательный actual ASM diff. Цель — проверить конкретную форму dispatch/code placement без изменения batch width4, входов, loops, thresholds или allocation policy. Это не утверждение, что batch сейчас должен быть cold: на dense input он как раз доминирует.

До принятия timing-работы следует получить normal full-TU object/ASM точного нового executable: действительно ли исчезли инструкции/ветвления в multibyte path, изменились ли loop fallthrough, branch distances, register spills, frame и горячий размер? Если compiler восстановил ту же форму, source refactor можно оставить исследовательской заметкой; обязательного нового бенчмарка из него не следует. Artificial noinline может добавить call/return и испортить плотные runs; forced inline может увеличить code size или продублировать continuation tail. Любой такой вариант — самостоятельная заранее названная альтернатива, не молчаливый «ремонт D2».

Даже реальный ASM diff не доказывает, что он объясняет прежние5–7%. Измеряется новая реализация на новом controlled executable; causal attribution старых результатов без дополнительного доказательства не появляется.

## Как сравнивать, если гипотеза дойдёт до измерений

Нужны свежие B, D1, D2 и D3 с одним fixedB prerequisite, compiler/flags, immutable physical seed и backend-linked native module; B/T — exact twins одного prefix/ELF/module на разных data copies. Старые D2 проценты сохраняются историей, не заменяют свежие D2/B или D3/D2 пары. Нельзя выдавать D1/D2/D3 за twins: это разные source variants.

С B/T это **пять ролей**. Прежний4-role Williams block нельзя просто дополнить пятой ролью. До запуска фиксируется отдельный сбалансированный5-role schedule и его counts, все10 role pairs и две cohorts; например уже использованный в старом startup/decoder screen подход —5 forward orders и их reverse. Число rounds/loops и формат результата выбираются до новых outcomes; повторение grid или поиск cutoff по полученным процентам не входит в гипотезу.

Существующие18 native +7 whole-SQL cases дают полезный неизменный первый screen: one/tails проверяют границу «first + remaining3», batch4/5/8 — правильный crossover, dense/multi/singletons/growth — segment/allocation paths, delta2–7 — scalar continuation длины. Полный generated-TID oracle и проверка compressed bytes/checksum/consumed обязательны. Release и assert qualification идут до timing; все absolute samples, spreads, exact twins, negatives и whole-command units сохраняются.

Граница покрытия остаётся существенной: существующие delta cases почти однородны по длине; они не исчерпывают переходы1→2→1 и произвольную позицию multibyte byte внутри неудавшейся попытки batch, а также все input/output-capacity совпадения. До timing нового pointer-contract нужны отдельные **нетайминговые valid-input** проверки таких переходов и состояний «1/2/3 свободных output slots», не outcome-tuned новый performance grid. Семь SQL не дают полного actual-AM/rescan/concurrency покрытия, native inner CPU включает allocation/materialization/free и не равен чистой цене varbyte primitive. Ускорение D3, устранение scalar regression или общий SQL выигрыш сейчас не заявляются.
