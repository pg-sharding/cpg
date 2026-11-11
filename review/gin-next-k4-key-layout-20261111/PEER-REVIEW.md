# Read-only peer review: K4 compact scan-key layout

Проверено 2026-11-11 около06:33 UTC. Объект: `review/gin-next-20261111/cache-key-layout/`, parent `ec32d586cf3bb6cfa76eb672db70160b436ce47c`. Исходники, patch и metadata не менялись; patch не применялся, backend не собирался и не запускался. Проверка использовала parent bytes из read-only Git, текст diff, архивные normal-TU ASM и декларативную Python ctypes модель LP64 ABI.

**Блокирующих ошибок в ожидаемой раскладке не найдено.** Перенос `nadditional` после `nrequired` заполняет четырёхбайтовый gap перед `additionalEntries` и устраняет отдельный gap после прежнего `nadditional`. На обычном LP64 ABI итоговый размер уменьшается160→152 байта. Это ожидаемая раскладка по типам, не измерение K4 backend и не доказательство улучшения скорости.

| Поле / размер | K3 | K4 expected |
|---|---:|---:|
| `nrequired` | 24 | 24 |
| `nadditional` | 40 | 28 |
| `additionalEntries` | 32 | 32 |
| `entryRes` | 48 | 40 |
| `boolConsistentFn` | 56 | 48 |
| `triConsistentFn` | 64 | 56 |
| `consistentFmgrInfo` | 72 | 64 |
| `triConsistentFmgrInfo` | 80 | 72 |
| `collation` | 88 | 80 |
| `query` | 96 | 88 |
| `queryValues` | 104 | 96 |
| `queryCategories` | 112 | 104 |
| `extra_data` | 120 | 112 |
| `strategy` | 128 | 120 |
| `searchMode` | 132 | 124 |
| `attnum` | 136 | 128 |
| `excludeOnly` | 138 | 130 |
| `curItem` | 140 | 132 |
| `curItemMatches` | 146 | 138 |
| `recheckCurItem` | 147 | 139 |
| `isFinished` | 148 | 140 |
| `triCache` | 152 | 144 |
| `sizeof(GinScanKeyData)` | 160 | 152 |
| alignment | 8 | 8 |

Модель предполагает pointer/Datum size8/alignment8, int32/Oid size4/alignment4, uint16/StrategyNumber/OffsetNumber size2/alignment2, bool size1, шестибайтовый ItemPointerData с alignment2. Она соответствует displacement существующего x86-64 normal ASM. Для 32-bit ABI и иных packing options числа не заявляются. Фактические K4 `sizeof`/`offsetof` и normal objects следует подтвердить на целевой сборке, прежде чем менять статус UNCOMPILED.

Проверка provenance:

- `parent-gin_private.h` точно совпадает с header из указанного Git parent:18542 байта, SHA256 `cb6b3a876c1ec8fa2621eae95d5e7f3e3b4a7ef86fc5bfa8cd52415e96aa1fb0`.
- `SOURCE-PREP-r1.json.source_sha256 = 8feb606e…` соответствует **будущему изменённому header**, реконструированному в памяти единственной перестановкой строк. Это не digest `parent-gin_private.h`; совпадение modified bytes подтверждено. Желательно назвать поле `expected_modified_header_sha256`, чтобы проверяющий не принял его за сохранённый parent.
- Patch SHA256 `78a8796a505a39568018061472056f87021b68d9f385daa3beaf051ebd374a93` совпадает с400-байтовым diff. Только одна перестановка полей, никаких callback/policy изменений.
- SHA256 всех трёх ссылочных normal-ASM файлов B/K1/K3 совпали с metadata. Для `directTriConsistentFn` независимо извлечено тело до следующего symbol: у всех address `0x30`, body SHA256 `25694193dab75ab0965355eb97d9a0b4537f3b339c31724ca38aef7f3f88f1d9`. Сюда входит trailing alignment перед следующим helper, то есть совпадение сильнее только совпадения C body.

Совпадение normal object direct helper опровергает только узкую версию гипотезы «K3 изменил этот helper body/address в объекте». Оно не устанавливает равенство адресов после final link, caller codegen, surrounding hot code, allocator placement, cache-line alignment или стоимости K3 initialization. Из него нельзя вывести причину старых +2.62/+3.02% либо обещать их устранение K4. Новый compact layout также сдвигает все поля после `additionalEntries`, следовательно меняет load displacements и потенциально code size; это проверяется в будущих actual objects.

Контракты по исходникам выглядят совместимыми с перестановкой: `ginscan.c` выделяет массивы через `palloc_array(GinScanKeyData, ...)`, копирует через `sizeof(GinScanKeyData)`; доступ к counters идёт по имени поля. В просмотренных GIN paths не найдено hardcoded sizeof/offsetof, сериализации этой структуры или positional aggregate initializer. Обязательна согласованная пересборка всех потребляющих TU/моделей; смешивать старые objects с новым private header нельзя. Это внутренний scan-state layout, а не on-disk format change.

Размер152 совпадает с размером B до добавления `triCache`, но **не возвращает B offsets**: у B `entryRes=48`, у expected K4 `entryRes=40`. Поэтому «K4 восстанавливает baseline layout» было бы неверно. Кроме того, экономия8 байт в запросе с одним key не доказывает уменьшение числа затронутых cache lines: нужны фактическая alignment базы и обращения. K3 cache allocation остаётся отдельным объектом и сохраняется; compact key не устраняет его стоимость.

Корректная текущая формулировка: одна проверяемая source-layout гипотеза поверх K3, с ожидаемым уменьшением структуры на8 байт на LP64. Build/qualification/performance evidence пока отсутствует в просмотренных трёх входных файлах; ни исходная dense regression, ни threshold64 не признаны исправленными.
