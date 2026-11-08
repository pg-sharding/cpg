# История экспериментов по ускорению индексов PostgreSQL

Срез 8 ноября 2026 года. Это сводка **существующих** результатов, включая неудачные варианты, исправления методики и незавершённые работы; новых замеров при её подготовке нет. Старые frozen bundles не изменены. «Оставлен RFC» означает воспроизводимый эксперимент для обсуждения, а не рекомендацию мержить. Сохранённый исходник или опубликованная ветка также не означают положительного performance-результата.

Практически полезные SQL-сигналы есть: ранние FTS position unions, большие intarray/GiST tsvector inputs, длинные SP-GiST text labels; позднее — typed int8 positioning, разреженные GIN conjunctions, demand decoding GIN, uniform hash probes и повторные hash rescans. Одновременно ни один из поздних общих кэшей/dispatch-вариантов не доказал универсальное отсутствие регрессий. Ниже удачный случай всегда соседствует с ограничением.

## Как читать числа

* Ratio = candidate/reference; меньше 1 быстрее. Снижение времени на 14.7% соответствует speedup 1.172×, а не 17.2%.
* В ранних таблицах явно используются отношения медиан; в поздних — median **непосредственных парных отношений**. Делить независимо агрегированные медианы, чтобы восстановить paired ratio, нельзя. Все min/max/raw находятся по ссылкам на исходные отчёты.
* Baseline ранней общей sort-волны — `4848fd6752ad6b88c5a066442df35ba208dfcec5`; исходная CF 6418 trgm-волна — `51d7bf5edca`; ноябрьские B-tree/AM — `72b9498df9a369e747f8d96efb5a6cd33c2451e2`. Они **не объединены** в один benchmark и не сравниваются друг с другом абсолютными временами. У intarray nplus отдельно раскрыта смешанная provenance runtime/extension.
* C helper/native kernel, executor Execution Time, client CREATE INDEX/COPY и целый application workload — разные метрики. CREATE INDEX для runtime B-tree/G1/G2/H1/H2/S1/S2 обычно только создаёт fixture и не является измеренным ускоряемым путём.
* Два placements/restarts на shared VM не равны независимой аппаратной репликации. Exact-ELF twin показывает вариацию условий при одном коде, но не доказывает ASLR/host noise как причину. Контроли не вычитаются из выигрышей; outliers не удалены. Bootstrap CI в первичных отчётах условны на конкретный process/cohort, не на новую машину.

## 1. Ранние сортировки: 14 независимых draft-концепций

Источник: [README](../sort-experiments-20261028/README.md), [77 SQL comparisons и диапазоны](../sort-experiments-20261028/BENCHMARK-RESULTS.md). Общая база 4848fd…, GCC 13.3/-O2 assertion/debug. Несколько первоначальных backend images содержали независимые core+extension изменения; отчёт раскрывает это, и ниже не придумываются новые one-patch замеры. Альтернативы одного callsite не являются серией.

| Концепция / draft | Реальный результат | Минус / статус |
|---|---|---|
| SP-GiST text direct label map | Long-text CREATE INDEX790.114→674.272 ms, ratio0.8534, **−14.7%** | Short text1236.678→1230.386 ms почти flat; repeated noisy. Узкий положительный случай |
| SP-GiST box direct median selection | Random CREATE INDEX1318.916→1283.878 ms,−2.7%; ordered−0.8% | Geometric NaN/zero fallback/detection costs; не крупное общее ускорение, selection prior art |
| SP-GiST KD partition selection | Random1566.464→1499.520 ms,−4.3%; ties≈flat | Микро detection/fallback может стоить дороже; не новое семейство алгоритмов |
| SP-GiST typed page-offset sort | Helper-положительный результат | Point CREATE INDEX1561.867→1560.220 ms flat, textshort+0.4%; полезный SQL-эффект не установлен |
| pg_trgm word typed sort | `show_trgm`/word workloads basic5.465→4.882 ms; repeated15.713→10.796; Unicode13.561→10.109: **−11…31%** | Это word/comparator workload, не весь GIN build; typed sorting уже PostgreSQL practice |
| pg_trgm word radix | Repeated15.713→9.994 ms, Unicode13.561→9.525 | Basic+1.2%; ordered/identical n54 в micro≈3.7–3.9× медленнее. Независимая альтернатива |
| GiST tsvector CRC radix | Doc2048 CREATE INDEX103.629→29.647 ms, **3.50×**; doc128:28.248→25.911 | Doc8≈flat; signed-edge dictionary n129 micro +26%; dispatch не универсален |
| intarray radix | Scalar sort n=16384:113.918→12.551 ms, **9.08×**; index a512:87.373→54.561, a4096dup:27.092→11.532 ms (**1.60–2.35×**) | Dictionary16/signed-edge n257 micro1.8–2.2× медленнее; дальнейший bounded-dictionary фикс ниже |
| BRIN merge instead of resort | Sorted INSERT109.184→97.041 ms, **−11.1%**; CREATE INDEX≈−1.9%, summarize≈−1.0% | Существующий TODO/merge prior art; mixed candidate содержит и tuplesort. Unsorted helper+15.5%, scratch O(n) |
| Tuplesort bucket bitmap | End-to-end ratios≈0.98–1.007 | Устойчивого SQL-ускорения нет; ordered n256 micro +4.6% |
| FTS typed positions | Duplicate512:151.695→130.225 ms; reverse512:185.161→158.860; parser-boundary2048:231.940→217.659 | Weight/truncation/position semantics существенны; дальнейший ordered-run вариант отдельно |
| FTS prefix bitmap | Dense224.353→36.085 ms (**6.22×**), spread400.360→74.493 (**5.37×**) | Small≈+1.1% noisy; sorted n64 helper≈1.73× медленнее; позже найден и исправлен high-position regression |
| VACUUM typed offsets | Hot≈+0.4%, ordered≈+2.8% | Полный VACUUM не ускорился |
| VACUUM bitmap offsets | Hot≈−1%, ordered≈+0.3% | В пределах scatter; не установлено SQL/VACUUM ускорение |

Штатные core 239, extension tests, differential/oracle/ASan helper checks выполнены в ограниченном объёме первичных отчётов; это не full-server sanitizer/fuzz proof. Эти 14 drafts и последующая перепаковка не дают права назвать приёмы новыми алгоритмами.

## 2. FTS followups и первые четыре подготовленных треда

[138 SQL comparisons](../fts-followups-20261029/BENCHMARK-RESULTS.md), [находки и исправления](../fts-followups-20261029/findings.md). Пять повторов+warmup, отдельный seven-repeat array probe; эти кампании не pooled.

| Направление | Результат и решение |
|---|---|
| Ordered prefix runs + bitmap | Исправлена реальная регрессия **нашего** старого bitmap: high33 positions master33.129 ms / old52.803 / fixed21.789. Dense236.634→37.161 ms, spread426.029→73.810; большие выгоды сохраняются. Boundary proof использует sorted/unique входные lexeme lists; touching/weight/global truncation не упрощены |
| Ordered-runs-only alternative | Disjoint pair7.664→2.391 ms. Это другая альтернатива тому же callsite, не следующий патч поверх bitmap |
| Input lexemes typed | Raw input random2048:562.675→516.777 ms, reverse128:391.319→351.301; helper ratio0.469 на random2048. SQL-эффект меньше micro |
| Rank operands typed | Duplicated query128:35.448→26.264 ms, random128:63.051→56.057. Helper ratio0.629 |
| Rank document representation typed | Interleaved32:2103.825→1840.346 ms; helper ratio0.360. Не заявлено такое же ускорение всего ranking-приложения |
| array_to_tsvector typed | **Не выбран**: longprefix32 789.829→926.209 ms; independent7repeat longprefix+10…15%, sorted≈+7.6…8%. Faster isolated comparator этого не отменяет |
| Array noinline mitigation | Longprefix ratios0.978–0.990, но random32 ratio1.135 с большой вариацией. Не признан regression-free replacement |
| GiST CRC larger typed cutoff | На actual CRC short words n256 oldradix1519 ns→typed3457; rejected |
| CRC first32 sampling | Biased-prefix trap1858→2943 ns, **+58%**; rejected, не SQL результат |
| 16-bucket/small radix | n256 CRC3069 ns против 1519; n512≈2.38× хуже. Rejected |

[Перепаковка](../fts-gist-intarray-new-threads-20261029/README.md) дала **4 новых UNSENT thread drafts / 8 attachments**: positions(3 альтернативы), input/ranking(3 patch series), GiST tsvector(1), intarray(1 diff-only). Это упаковка уже измеренного кода, не 8 новых performance-экспериментов. Array/noinline/CRC sampling/small radix оставлены отрицательными контролями, не включены как принятые attachments. [GiST results](../fts-gist-intarray-new-threads-20261029/03-gist-tsvector/RESULTS.md), [intarray results](../fts-gist-intarray-new-threads-20261029/04-intarray/RESULTS.md).

## 3. Intarray: исправления crossover, union arity и ещё не измеренные аналоги

Bounded dictionary+ordered guard исправляет старый n257 crossover: dictionary sort 6.661→3.075 ms, prepare 3.941→1.590; signed-edge sort 5.392→2.817. Большие scalar/index gains сохраняются, но dictionary 257 CREATE INDEX 33.540→33.470 ms **flat**. Нельзя выдавать scalar 2× за index 2×.

Оставшийся контрпример: **17-й distinct key в самом конце**. n257 master 1048.3 ns / plainradix 2341.1 / attached 2723.6: **2.60× master**, ещё 16–17% сверх radix; n512 attached 4091.4 против master 2009.7 ns. Отброшенный unbounded dictionary доходил до 4.12× потерь на collision chains; финальная попытка ограничивает size≤512 и collision work, но late 17 не устраняет.

[Small-n union](../intarray-smalln-20261030/REPORT.txt): existing n2 merge против concat/sort уже полезен; расширение до n5/n8 помогает только когда GiST действительно вызывает higher arity. Пять single-column fixtures наблюдали **только n2**. В двухколоночном случае n2 занимал 81920 вызовов, n5 —4729; там отдельный completed followup n2 **2314.591[2305.393,2333.006]ms**, n5 **2013.653[2002.547,2043.354]**, paired speedup 1.153× (−13.0% elapsed); n8 2026.599 ms, дополнительного выигрыша над 5 не установлено. На ordered-disjoint n5/len 128 helper 696.2→2375.3 ns, а на tiny n5≈2.4× хуже: arity-only cutoff не универсален.

[Отдельно скомпилированный nplus](../intarray-nplus-20261030/README.txt) был более строгим physical-reset/PRNG экспериментом, но сохранённый [summary](../intarray-nplus-20261030/full-results/summary.txt) имеет **PARTIAL**, а STATUS всё ещё исторический RUNNING. В нём только single_small: n2/n5/n8≈229.259/229.534/229.519 ms, flat. Это **не** завершённое подтверждение multicOLUMN gains предыдущего smalln. RuntimeHEAD 1b0b45… и отдельный extension blob 98711ac… раскрыты в README; приписывать это чистому single pinned upstream нельзя.

[Source-only analogues](../intarray-analogues-20261030/REPORT.txt): penalty/picksplit cardinality без materialized union, fixed-gap compression selection, multirange sorted merging, btree_gist delayed min/max materialization, GiST-specific removal of redundant uniqueness pass. **Новых runtime изменений/бенчей здесь нет**. Уже линейные numeric unions, OR-signatures trgm/hstore и merge tsvector не являются тем же concat/sort bottleneck.

## 4. pg_trgm GIN: adaptive/bitmap/radix 6/MSD и прямое предыдущее обсуждение

[Исходный adaptive report](/Users/reshke/pgcf-new/waves/cf62-trgm-gin-6418/bench-report.md) находится вне этого repo по абсолютному пути, зафиксированному в source catalog; локальная ссылка на него ниже дана отдельно. Его baseline 51d7bf… отличается от следующей controlled трёхсторонней кампании 4848fd… .

Исходная 0002 radix регрессия на repeated подтверждена clean binary: **2.60–2.62→3.08–3.11 s (+18.4%)**, interleaved instrumented 2715→3097 ms (+14.1%); live sort+uniq 789 против 390 ns/row. Старое «опровержение» было невалидно: pg_ctl запускал соседний один и тот же postgres/.so. Adaptive bitmap для 33…128 elements уменьшил standalone repeated штраф до≈+3.4%, сохранил long≈−7.9%; fullv 11+accounting+adaptive ss 11.593→6.981 s,ll 10.321→5.661 s, но repeated 2.613→2.769 (+6%). Эти full-series gains включают GIN hash и другие патчи, не принадлежат одной сортировке.

Новая [триада на 84](../trgm-three-approaches-84-20261028/REPORT.txt),5 timed repetitions:

| Подход | Bare master: short / long / repeated / Unicode секунды | Fullv11 baseline: short / long / repeated / Unicode секунды | Решение |
|---|---|---|---|
| Reference | 11.763 /10.618 /2.775 /2.033 | 7.711 /5.906 /3.244 /1.460 | Разные references, не смешивать |
| Bitmap buckets | 11.724 /9.559 /2.975 /1.922 | 7.360 /5.694 /2.996 /1.415 | Поверх v11 −3.1…7.7% во всех 4 наборах; bare repeated **+7.2%**, не универсальная замена master |
| Smaller radix6 | 11.874 /9.510 /3.037 /1.915 | 7.343 /5.716 /3.101 /1.431 | Поверх v11 −2.0…4.8%; bare repeated **+9.5%**. Long разница с bitmap меньше разброса |
| In-place MSD | 11.800 /10.572 /2.888 /2.057 | 7.361 /6.731 /2.950 /1.554 | Fullv11 long **+14.0%**, Unicode **+6.4%**; не выбран. Lowercutoff8 улучшает longmicro≈10%, но repeatedmicro +32% |

Пересечение с [Geier's GIN thread](https://www.postgresql.org/message-id/5d366878-2007-4d31-861e-19294b7a583b%40gmail.com) **прямое для этих старых trgm sorting/adaptive/MSD экспериментов**. Нельзя представлять radix, малый qsort fallback, bitmap dispatch или сортировку trigram representations как впервые найденную нами тему. Детальный новый [thread comparison](gin-thread-comparison-20261108/GIN-THREAD-COMPARISON-20261108.md) прочитал 52 archive messages/59 attachments v1–v11 и public continuation, а также collation companion 21 messages/15 attachments. По G1/G2 ниже прямого дублирования не найдено по конкретным функциям/структурам; это не доказательство абсолютной новизны. Thread не «только CREATE INDEX»: trgm query extraction и GIN pending-list cleanup тоже используют некоторые из его путей.

## 5. Все 24 legacy B-tree варианта

[Полный source index](git-publication-legacy/legacy-source-index.json) связывает каждый diff с pinned source и Git-веткой; aliases/staging копии не считаются отдельными экспериментами. Ниже 24 строки точно по этому каталогу. Они частично совпадают с версиями текущего 31-version index, поэтому **24+31 нельзя назвать 55 уникальными патчами**.

| Вариант | Механизм | Измерение / отрицательный контроль | Решение и первичный отчёт | Исходник |
|---|---|---|---|---|
| ios-v1 | Eager cache Datum/isnull posting tuple | 8TEXT micro20.906→5.721 ns/key; wideCOUNT −13…15% в A/B/C, но D123.952→131.871 ms; singleton хуже во всех 4 блоках | [Superseded, не merge-ready](../btree-novelty-20261106/RESULTS.md) | [Git](https://github.com/pg-sharding/cpg/tree/review/index-opt-20261107/legacy-ios-v1) |
| ios-v2 | Lazy fill после visibility, singleton-page fastpath | WideCOUNT −12.2…15.0%, projection−9.5…15.8%; narrow1INT4/2TID +4.13/+6.85% в audit | [Узкий положительный prototype, далее v3](../btree-followups-20261106/ios-cache-v2/findings.md) | [Git](https://github.com/pg-sharding/cpg/tree/prototype/btree-ios-cache-v2-20261106) |
| ios-v3 | Запрет cache при одном index attribute | Wide8COUNT paired.8475/.8511; устраняет часть v2 одноатрибутного расхода. Позже 2/3-attr short-run +4.6…5.8% в discovery/confirmation | [Reference эксперимент, narrow/LIMIT/heap costs открыты](../btree-regression-fixes-20261107/ios/RESULTS.md) | [Git](https://github.com/pg-sharding/cpg/tree/review/index-opt-20261107/ios-v3) |
| ios-v4 | Scalar one-pass value/null copying | Corrected actual-helper32TEXT/highreuse более+200% против v3 | [Rejected до нового SQL](../btree-stress-20261107/ios/RESULTS.md) | [Git](https://github.com/pg-sharding/cpg/tree/review/index-opt-20261107/legacy-ios-v4) |
| ios-v5 | Chunk/unrolled copy вместо широкого scalarv4 | 4INT4 kernel≈−27%, wide8SQL gain против master сохранён, но heap4 +4.52/+7.72% против v3; short SQL mixed | [Не выбран](../btree-stress-20261107/ios/RESULTS.md) | [Git](https://github.com/pg-sharding/cpg/tree/review/index-opt-20261107/legacy-ios-v5) |
| ios-v6 | Constant memcpy2/3/4, wider bulk unchanged | Confirmation narrow v6/v3≈.965/.969, но v6/B≈1.005/1.013; wide32 gain35–50%. Mainw8+65.35% толькоодин placement, не повторился | [Не выбран как полное исправление; retained current control](../btree-next-20261107/ios/RESULTS.md) | [Git](https://github.com/pg-sharding/cpg/tree/review/index-opt-20261107/ios-v6) |
| separator-cache-v1 | 64direct-map internal int8 arrays, admission2 | Absent cache/typed+3.5…11%; fresh2+15.7…20%; typed — основная часть выигрыша | [Superseded cache design](../btree-followups-20261106/separator-cache/findings.md) | [Git](https://github.com/pg-sharding/cpg/tree/prototype/btree-separator-cache-20261106) |
| typed-v1 | Internal-only int8 direct tuple comparator | Нужный independent control: old cache не даёт устойчивого бонуса; short latency лучше расширенного typed2 | [Attribution alternative, не universal optimization](../btree-followups-20261106/separator-cache/findings.md) | [Git](https://github.com/pg-sharding/cpg/tree/review/index-opt-20261107/legacy-typed-v1) |
| separator-coldfix | Original internal-only search +admission64/deferredcallback | Hot CPU0 лишь≈−0.6%master, +2.5%old typed; exact2 восстановление непостоянно | [Negative alternative, core 239](../btree-regression-fixes-20261107/separator/findings.md) | [Git](https://github.com/pg-sharding/cpg/tree/review/index-opt-20261107/legacy-separator-coldfix) |
| separator-cache-v2 | Per-descent eligibility, typed leaf, admission64 | Hot/master≈−10…13%, но cache/typed лишь≈−2.3%; absent/typed+2.8…5.8%, потом+4.53/+12.76%. Admission64 eagercopy и stride8underuse доказаны | [Published узкий prototype, cache experimental](../btree-stress-20261107/separator/findings.md) | [Git](https://github.com/pg-sharding/cpg/tree/prototype/btree-separator-cache-v2-20261107) |
| typed-v2 | Same gates/leaf direct int8, без cache arrays | В позднем head-to-head hottyped/B.9114/.8875; samepivot.8471/.8616; больше простоты, без cache lifetime. Inherited permanent/WAL/recovery gates/unusedbuf | [Более перспективный самостоятельный путь, далее V3–V6](../btree-next-20261107/separator/REVIEW.md) | [Git](https://github.com/pg-sharding/cpg/tree/review/index-opt-20261107/typed-v2) |
| typed-conditional | Conditional bound updates | Сохранённый independent control; GCC всё равно выдаёт direction branches. Нет доказанной branchless SQL победы | [Не выбран отдельно](../btree-regression-fixes-20261107/separator/findings.md) | [Git](https://github.com/pg-sharding/cpg/tree/review/index-opt-20261107/legacy-typed-conditional) |
| typed-maxguard | Check nonNULL max pivot перед typed loop | Eytz/maxguard hot.9578/.9535, absent1.0153/1.0396; это лишь matchedcontrol, не стабильный отдельный победитель | [Не выбран](../btree-regression-fixes-20261107/separator/BENCHMARKS.md) | [Git](https://github.com/pg-sharding/cpg/tree/review/index-opt-20261107/legacy-typed-maxguard) |
| separator-eytzinger | Readonly derived Eytzinger internal array+maxguard | Hot Eytz/cache v2 1.0284/1.0071; wide/no consistent increment.2018 Eytz discussion direct prior art | [Correctness positive, performance mixed/negative](../btree-regression-fixes-20261107/separator/BENCHMARKS.md) | [Git](https://github.com/pg-sharding/cpg/tree/review/index-opt-20261107/legacy-separator-eytzinger) |
| separator-midpoint | Cached midpoint(low+high)/2 | Asm короче; hot/v2 1.003/.999, samepivot1.0088/.9958; fresh65−5.54/+7.54%,CPU−2.6/−3.3% | [Не выбран: no replicated repair](../btree-stress-20261107/separator/findings.md) | [Git](https://github.com/pg-sharding/cpg/tree/review/index-opt-20261107/legacy-separator-midpoint) |
| hybrid-tail4 | Packed-order TID compare+linear tail4 | Actualn64 ordered22.78→14.01 ns. Logged SQLdense.9941/short1.0032/append1.0492; zero-helperappend тожедвигается | [Micro-positive, SQL unresolved](../btree-regression-fixes-20261107/hybrid/BENCHMARKS.md) | [Git](https://github.com/pg-sharding/cpg/tree/prototype/btree-posting-hybrid-20261106) |
| hybrid-tail8 | То же, tail8 | n64 random47.00→29.71 ns, ordered14.48 ns против tail4:14.01; зависитот shape | [Alternative, no new establishedSQLgain](../btree-regression-fixes-20261107/hybrid/BENCHMARKS.md) | [Git](https://github.com/pg-sharding/cpg/tree/review/index-opt-20261107/legacy-hybrid-tail8) |
| posting-comparator | Normalized packed TID order без tail | n64 ordered22.78→15.12 ns; loggedSQLdense1.0516/short1.0176/append1.0187 | [SQL не подтверждает kernel gain](../btree-regression-fixes-20261107/hybrid/BENCHMARKS.md) | [Git](https://github.com/pg-sharding/cpg/tree/review/index-opt-20261107/legacy-posting-comparator) |
| hybrid-noinline | Та же tail4 логика, outlined helper | Caller623Bbaseline/780Bhybrid→409B+340Bhelper; loggeddense1.0216/short1.0119/append1.0352 | [Code-size наблюдение, SQL победы нет](../btree-regression-fixes-20261107/hybrid/findings.md) | [Git](https://github.com/pg-sharding/cpg/tree/review/index-opt-20261107/legacy-hybrid-noinline) |
| posting-block-first-0 | Сначала block binary search, затем offset; tail0 | n64 ordered17.96 ns против tail4:14.01 | [Отрицательный actual-body alternative](../btree-regression-fixes-20261107/hybrid/BENCHMARKS.md) | [Git](https://github.com/pg-sharding/cpg/tree/review/index-opt-20261107/legacy-posting-block-first-0) |
| posting-block-first-4 | Block-first +tail4 | n64 ordered16.55 ns против 14.01; different-block random51.38 против 34.18 | [Не выбран](../btree-regression-fixes-20261107/hybrid/BENCHMARKS.md) | [Git](https://github.com/pg-sharding/cpg/tree/review/index-opt-20261107/legacy-posting-block-first-4) |
| compact-v1 | Dense TID array +tuple/run descriptors | BTScanOpaque27352→21400B **−21.8%**. MainSQLduplicate/short1.194/1.142, freshconfirmation.981/1.010 | [Memorywin, robustSQLgain неустановлен](../btree-other-approaches-20261107/posting/findings.md) | [Git](https://github.com/pg-sharding/cpg/tree/review/index-opt-20261107/legacy-compact-v1) |
| compact-v2 | Small-run scalar-copy refinement | Actualposting4packing base464.13/v1 442.79/v2 485.32 ns; combinedv21238.43 vs v11183.08. Старый packing regression не повторился actualbody | [Не продвигать](../btree-other-approaches-20261107/posting/findings.md) | [Git](https://github.com/pg-sharding/cpg/tree/review/index-opt-20261107/legacy-compact-v2) |
| lazy-dedup-v1 | Temp page только после первой mergeable пары | Failedpassint8 11.228→6.283 µs; COPYint8flat,text random+5%,single +3%. Conditional calibrated opportunity≈0.5–1.1%COPY | [Нет SQLgain; timing ELF receipt не доказан; НЕ CREATEINDEX путь](../btree-other-approaches-20261107/lazy-dedup/RESEARCH.md) | [Git](https://github.com/pg-sharding/cpg/tree/review/index-opt-20261107/legacy-lazy-dedup-v1) |

### Что именно прояснили B-tree followups

* **Cache/base ≠ cache gain.** В отдельном неизменённом-ELF сравнении cache/typed hot 0.9491/0.9906, same-pivot absent **1.0248/1.0243**, randomabsent 0.9336/0.9965; typed/base hot 0.9114/0.8875. Потому рекомендация стала «выделить typed-only, cache оставить experimental». [Source/profiles/invalidation](../btree-next-20261107/separator/REVIEW.md).
* **Admission frequency измерена отдельно.** Cache state visits63 invalid,64 valid с eager copy 283+9 pivots; writeLSN block3 invalidates/reset visits1 и 63 probesreadmit, непосещённый изменившийся block289 не сбрасывает block3. Это correctness/lifetime trace, не throughput improvement. Relation-stride 8 распределял 32/96 relations лишьпо 8 из 64 slots; новый hash не реализовывался.
* **Hybrid имеет маленький Amdahl budget.** 306433/386138 helpercalls на 500 krows; иллюстративные 10 ns/call дают 3.1/3.9 ms при≈1 secondINSERT. Это расчёт, не измеренный SQL выигрыш. Old source-generation/temp/WAL confounds и corrected prepared-input campaign разделены; noinline/micro не доказывают I-cache cause.
* **Compact экономит память, но переносит работу в return path.** 128-entry packing 262.78→34.77 ns/batch,return 569.05→714.73;combined 828.29→750.36. LIMIT 1 materializes 1886712 TIDs ради 10 kreturnedrows; само compactcopy это eagerwork неустраняет.
* **Lazy dedup win редок в append-only.** При завершённом distinctCOPY без deletion/VACUUM/abort/других writers failedpasses≤leafsplits≤finalblocks−2; bound 0.274–1.394%inserts. Micro×bound даёт calibrated≈0.53–1.13%COPY, **не строгий walltime bound**. Bottom-up/versionchurn,LP_DEAD simpledeletion после postingoff−1,page reuse/errors исключены. Старые source совпадают diff, но связь retainedELF с прежними timingrows не доказана SHAreceipt. Нового runtimefix/measurement в reanalysis не было.

## 6. Текущая волна:31 версии в 8 семействах

[Current source publication index](git-publication/source-publication-index.md) содержит 31 code-only ветку: версии независимы относительно 72b949…, не серия для совместного наложения. Git status/remote hashes фиксируются отдельными publication receipts; performance status берётся из отчётов, а не из факта push. Ниже перечислены все 31 версии; затем подробно итог каждой семьи. V11 phase0 preliminary и pending phase1, а также V12 source/ASM-only оговорены отдельно; окончательный V11 performance-вердикт не зафиксирован.

| Семейство | Версия / code-only branch | Исторический результат / статус |
|---|---|---|
| typed | [v2](https://github.com/pg-sharding/cpg/tree/review/index-opt-20261107/typed-v2) | Inherited cache gates/control; история выше |
| typed | [v3](https://github.com/pg-sharding/cpg/tree/review/index-opt-20261107/typed-v3) | TEMP/unlogged/recovery gates сняты, eligibility в generic descent; read gains/write-cold costs |
| typed | [v4](https://github.com/pg-sharding/cpg/tree/review/index-opt-20261107/typed-v4) | Eligibility из generic search в _bt_first, flag остаётся в key; не выбрана |
| typed | [v5](https://github.com/pg-sharding/cpg/tree/review/index-opt-20261107/typed-v5) | Generic/write key и binsrch возвращены к master; constant read-only wrapper; regression controls остаются |
| typed | [v6](https://github.com/pg-sharding/cpg/tree/review/index-opt-20261107/typed-v6) | Cheap rejection predicate reordered; actual 2 cohorts завершены, bounded RFC |
| ios | [v3](https://github.com/pg-sharding/cpg/tree/review/index-opt-20261107/ios-v3) | Широкий reference, narrow/LIMIT затраты |
| ios | [v6](https://github.com/pg-sharding/cpg/tree/review/index-opt-20261107/ios-v6) | Shortcopy2/3/4, unselected ранее |
| ios | [v7](https://github.com/pg-sharding/cpg/tree/review/index-opt-20261107/ios-v7) | Transition-only attachment: metadata tradeoff, не complete fix |
| ios | [v8](https://github.com/pg-sharding/cpg/tree/review/index-opt-20261107/ios-v8) | Page attachment/visible qualification, original _bt_returnitem; LIMIT/heap costs |
| ios | [v9](https://github.com/pg-sharding/cpg/tree/review/index-opt-20261107/ios-v9) | Identity-first hit skips flag; R2 actual costs сохраняются/history erratum |
| ios | [v10](https://github.com/pg-sharding/cpg/tree/review/index-opt-20261107/ios-v10) | likely annotation: hit fallthrough/jumps removed; actual 2 cohorts, не complete fix |
| ios | [v11](https://github.com/pg-sharding/cpg/tree/review/index-opt-20261107/ios-v11) | Stable cached natts; actual phase0 preliminary, phase1 PENDING |
| gin-advance | [v1](https://github.com/pg-sharding/cpg/tree/review/index-opt-20261107/gin-advance-v1) | Initial decoded-run skip candidate; historical negative |
| gin-advance | [v2](https://github.com/pg-sharding/cpg/tree/review/index-opt-20261107/gin-advance-v2) | Bounded upper_bound/gallop alternative, physical rotation erratum |
| gin-advance | [v3](https://github.com/pg-sharding/cpg/tree/review/index-opt-20261107/gin-advance-v3) | Убрана redundant comparison; actual sparse SQL gain, short-skip/OR losses |
| trgm-positions | [v1](https://github.com/pg-sharding/cpg/tree/review/index-opt-20261107/trgm-positions-v1) | Initial query signature-position cache |
| trgm-positions | [v2](https://github.com/pg-sharding/cpg/tree/review/index-opt-20261107/trgm-positions-v2) | Historical correctness/performance refinement |
| trgm-positions | [v3](https://github.com/pg-sharding/cpg/tree/review/index-opt-20261107/trgm-positions-v3) | Historical refinement; не отдельное принятое ускорение |
| trgm-positions | [v4](https://github.com/pg-sharding/cpg/tree/review/index-opt-20261107/trgm-positions-v4) | Similarity regression/control; extracted micro/rotation errata |
| trgm-positions | [v5](https://github.com/pg-sharding/cpg/tree/review/index-opt-20261107/trgm-positions-v5) | Similarity repair; actual SQL negative, REJECTED FOR MERGE |
| hash-rank | [v1](https://github.com/pg-sharding/cpg/tree/review/index-opt-20261107/hash-rank-v1) | Advisory rank+exact fallback; static native model erratum |
| hash-rank | [v2](https://github.com/pg-sharding/cpg/tree/review/index-opt-20261107/hash-rank-v2) | Actual exported entries/TU repair, replicated uniform SQL gain, skew/tiny losses |
| gin-lazy | [v1](https://github.com/pg-sharding/cpg/tree/review/index-opt-20261107/gin-lazy-v1) | Initial private compressed demand decode PoC |
| gin-lazy | [v2](https://github.com/pg-sharding/cpg/tree/review/index-opt-20261107/gin-lazy-v2) | Historical refinement/control, нефинальный actual reference |
| gin-lazy | [v3](https://github.com/pg-sharding/cpg/tree/review/index-opt-20261107/gin-lazy-v3) | Actual SQL≈65.5%gain selective; fair native full read11–12%loss |
| gin-lazy | [v4](https://github.com/pg-sharding/cpg/tree/review/index-opt-20261107/gin-lazy-v4) | postingData check толькона exhaustion; partial native repair, selective5–8%slowerV3 |
| hash-buffer | [v1](https://github.com/pg-sharding/cpg/tree/review/index-opt-20261107/hash-buffer-v1) | Validated page hint across rescans; narrow plain SQL gain confirmed, negatives |
| gist-box | [v1](https://github.com/pg-sharding/cpg/tree/review/index-opt-20261107/gist-box-v1) | Initial page-batch BOX predicate; historical actual |
| gist-box | [v2](https://github.com/pg-sharding/cpg/tree/review/index-opt-20261107/gist-box-v2) | Historical batch refinement |
| gist-box | [v2r2](https://github.com/pg-sharding/cpg/tree/review/index-opt-20261107/gist-box-v2r2) | Experimental RFC reference; NULL/dense costs retained |
| gist-box | [v3](https://github.com/pg-sharding/cpg/tree/review/index-opt-20261107/gist-box-v3) | 4 caller guards; actual NONSELECTED upgrade attempt |

### Typed-only V3→V6

[Final review](typed/deliverables-public-r2/REVIEW.md), [абсолютные времена, разброс и paired CPU](typed/deliverables-public-r2/BENCHMARKS.md). V3 снял cache-only gates permanent/WAL/recovery и unused buf. V4 перенёс eligibility в read initialization; V5 убрал flag/store/branch из generic key/binsrch, выделив constant read-only wrapper; V6 сначала отвергает неподходящее число keys и иной comparator. Generic search/binsrch normalized assembly и insert/utils .text совпадают с master; **весь ELF/весь write path не объявлен byte-identical**.

Actual V6: два cohort,2424 raw/2016 retained. Hot V6/B 0.9093/0.9042,V6/twin 0.8974/0.9011; absent V6/B 0.8776/0.8627; TEMP 0.9109/0.9005,UNLOGGED 0.9127/0.9034. TEMP/unlogged/physical standby actual oracle/counter подтверждают новую применимость. Oracle на той же locked page сохраняет NULL/truncated/internal-equality/TID fallback.

Оставшиеся минусы: fresh exact 1 **≈40–50 µs**,V6/B 1.1784/1.1946,V6/twin 1.0625/1.2143; cross-type int4 V6/B 1.0536/.9957,text 1.0415/1.0322. Append int4 CPU0 V6/B 1.0483,twin 1.0384; same-live-PID repeat 1.0575/1.0532. Heated profile≈9 µs у reference/candidate не объясняет cold cost; software-only 6992 samples/0 lost. Все 6 direct pairs/CPU, old V3/V4/V5 negatives и randomized unique INSERT сохранены. **Выбор: V6 bounded RFC, не regression-free merge.**

### IOS V7–V12: metadata, caller history и остающиеся издержки

[V7 checkpoint](ios/CHECKPOINT.md), [V8 tables 0](ios/V8-SQL-0.md)/[1](ios/V8-SQL-1.md), [V9 R2 result](ios/reporting-v9-r2/RESULTS.md), [V10 tables 0](ios/reports-v10/V10-SQL-0.md)/[1](ios/reports-v10/V10-SQL-1.md), [V11 design](ios/V11-DESIGN.md).

V7 transition-only attachment уменьшает forward posting 64 dispatch≈13.7% против V6, но reverse posting 2+32 singletons добавляет 13.1% в native kernel; полного SQL-исправления нет. V8 переносит attachment на page/visible consumer и возвращает upstream return body; wide 32 TEXT tail≈−50%, но LIMIT 1+4.62/+5.59%,LIMIT 2+6.59/+5.37% против base,heap 4+11.38/+11.30%. V9 identity-first hit не устраняет native cost: против V6 2 INT4 reuse2+7.51/+8.11%,reuse64+21.01/+20.37%,8 TEXT+9.18/+8.80%; широкий SQL gain сохраняется.

**Erratum V9/R2:** только измеряемый backend base выполнял дополнительные sequential reference/checksum SQL до ranking. Одинаковые ELF/copy не означают одинаковую историю persistent backend. Это потенциальный confound, не установленное объяснение всех процентов. V10 сделал 128 validation commands одинаковыми для всех roles; одновременно изменил source(likely hit annotation), поэтому V10/V9 не является matched causal comparison.

V10 actual 19 SQL/28 native, два cohort: wide 8 COUNT medians 63.3455→52.6910 ms и 60.9675→50.5320; TEXT 32 tail 24.2370→11.9095 и 23.4610→12.6525. Но native V10/V6 TEXT 32 NULL+20.90/+11.28%,TEXT 8+9.11/+8.34%,2 attr high reuse+14.95/−2.53%. SQL phase1 backward pair 58.8075→64.0600 ms,paired+7.60% против base/+9.14% twin; Seq 43.758→46.248 ms тоже ухудшается и не вычитается. V10 не выбран как полное исправление.

**V11** добавляет stable cached natts, убирая dependent descriptor load. После source/assembly/correctness preparation фактически завершён и root-аудирован **phase0**; [полные preliminary tables](ios/reports-v11/phase0-measurements.md) содержат1064 SQL raw/912 retained/152 warm и отдельные native данные. Например f2 paired V11/base−0.18%,V11/twin−0.97%,но LIMIT1+5.30/+2.91%,LIMIT2+6.04/+0.92%; native2INT4 reuse64 V11/V6+5.01%. Это **один preliminary cohort**, не финальный выбор. Phase1 ACK выдан, его завершённый результат на момент синтеза **PENDING**. **V12** — отдельный source/ASM-only probe, не завершённый SQL-эксперимент. Ни copy kernel, ни подсчёт jumps не обещают SQL gain.

### G1: decoded-run advancement

[Final decision](gin-advance/deliverables/gin-advance/DECISION.md). Strict upper_bound пропускает значения<=advancePast; сохраняются существующий 6-byte TID comparator, LOSSY sentinel и dropItem/RNG semantics. V3 убирает redundant compare после search. Два actual cohort: skew 1000 78.392→33.689 ms/79.914→35.2255,paired.4302/.4408; JSONB 158.9675→69.1305/155.294→64.841,.4249/.4166; phrase positive≈.50. **Это настоящий SQL-сигнал 50–58%, не build sort.**

Native pathA n1024 skip2 ещё+13.08/+12.85% против base(хотя−21/−19% против V2),skip4+23.14/+9.21%,skip0/1 тоже добавляют стоимость. OR SQL+4.76/+1.44% против B,+5.16/+1.50% против twin; array dense+1.69/+1.10%. V1/V2 raw и rotation errata не переписаны. **V3 выбран ограниченным review proposal, не универсальным ускорением.**

### G2: private compressed snapshot и lazy suffix decoding

[Final findings](gin-lazy/deliverables-public-v4/findings.md), [все числа](gin-lazy/deliverables-public-v4/BENCHMARKS.md). G2 владеет copied compressed snapshot после buffer unlock; он не удерживает указатель в shared page. Decode выполняется по требованию внутри selected suffix. Baseline уже умеет пропускать целые prefix segments. Новый codec/формат/WAL не предлагается.

V3 selective SQL≈−65.5% против baseline, но старая absence≈+13% и corrected balanced native full read+11–12%. V4 минимально уносит postingData check на exhaustion path. Actual V4 selective SQL≈−64% против baseline, но **V4/V3+5–8%** в selective cases; native full read починился лишь частично, остаток≈+6–9%. В новом cohort V3 absence сам почти flat(+1.65%B/+3%twin phase0),V4/V3.98816/.99835: исчезновение старых 13% нельзя приписать V4. Phase 1 V4 absence≈+6% сохраняется. **V4 bounded RFC/partial repair, не безусловный upgrade.** Старый unequal-dispatch kernel имеет erratum; прежние числа не подменены fair-dispatch результатом.

### S1: pg_trgm GiST signature positions

[Final decision](trgm-positions/publication-v5-final-r2/DECISION.md), [все 35 SQL/394 actual native cells](trgm-positions/publication-v5-final-r2/CONFIRMATION-RESULTS.md). Query signature-position cache должен учитывать siglen/opclass options, strategy/KNN identity, collation/cache contract и collision multiplicity. Простое bitset membership нельзя подменять числом совпадений без проверки контракта.

V5 исправляет большую similarity регрессию V4, но не показывает robust SQL gain. Phase 1 long LIKE+6.29/+8.23/+9.10% при siglen12/64/256,siglen1 absent LIKE+10.09%. Synthetic 476-trigram/non-full-signature actual native similarity ratio.39101/.39041 не переносится на SQL. All-ones/non-ALLTRUE stress key обычное compression нормализует в ALLTRUE; это не типичный stored-index gain. **REJECTED FOR MERGE**, история V1–V4/micro-fidelity/rotation errata сохранена.

### H1: advisory rank hash-page search

[Decision](hash-rank/deliverables/DECISION.md), [полные результаты](hash-rank/deliverables/BENCHMARKS.md). V2 сохраняет exact fallback bounds для uint 32/duplicates/overflow, исправляет native-entry fidelity/TU-caller confounds V1. Uniform point SQL−6.9…14.9% против B,−7.4…10.8% против twin; uniform absent−7.8…14.8% против B,−9.9…10.6% против twin.

Негативы: engineered overflow absence+3.51/+4.75% против B/twin в cohort0,+.30/+1.15% в 1; tiny forced до+4.71/+4.41%; native constant/skew до 2.30×/1.80× стоимости. Seq control тоже улучшается 1.7–4.4%, но не использован для normalization. **V2 promising uniform experiment, не broad replacement.** Interpolation/gallop — известные алгоритмы.

### H2: validated hash-buffer hint across rescans

[Final findings](hash-buffer/deliverables-public-v2/findings.md), [все 43 cells](hash-buffer/deliverables-public-v2/BENCHMARKS.md). Unchanged V1. Natural varying-residual case делает 3000 index rescans; Memoize включён, но узел Memoize не выбран планировщиком. Обычный Memoize control делает 1 actual probe и бонус reuse не получает.

Plain 32-probe query ms B/T/C: phase0 **2.100095/2.041147/1.855637**,phase1 **1.988988/2.034088/1.842627**. Direct C/B.87721/.92776,C/T.90014/.90609; CPU/B.87661/.92409,CPU/T.89653/.90038. EXPLAIN подтверждает тот же residual gain≈9–12%, но plain/profile throughput не подменяется EXPLAIN метрикой.

Plain absence C/B+2.05/+3.27%,C/T−0.70/+5.93%; tiny forced C/B+5.01/+4.58%,C/T−1.15/+5.20%. Random EXPLAIN phase0 C/B+10.29%,twin/B+11.22%,C/T+2.36%; не объявлен ни code cause, ни «просто noise». Actual getter shared same B 99.30/58.53 ns→C 57.22/32.75 ns — только native. **V1 узкий experimental RFC, не general merge-ready.**

### S2: batched built-in BOX predicates

[Final disposition](gist-box-batch/v3/SOURCE-DISPOSITION-ACTUAL.md), [curated findings](gist-box-batch/deliverables-public-v3/findings.md), [все 16 SQL×6 pairs](gist-box-batch/deliverables-public-v3/BENCHMARKS.md). Whole-page eligible built-in BOX helper сохраняет FP tolerance/NaN/infinity/conservative internal checks и leaf exactness; generic opclass callback не подменяется. На eligible page helper завершает **всю страницу**, даже если первые 8 all-pass; нет restart baseline/duplicate 8.

V3 — только 4 caller guards; native kernel тот же, что old V2 r 2, **новых V3 micro-чисел нет**. Sparse V3/B.57747/.60633,V3/T.57693/.59632(~39–42%gain),но V3/V2 r 2.99876/1.00083. NULL V3/old 1.01197/.99359,CPU1.02262/1.00126 — stable fix нет. Medium V3/old+4.10/+1.90%,allmatch forced+3.12/+1.45%; tiny forced phase1+16.54%(CPU+11.51%). Old V2 r 2 NULL 5–14% и dense full-read 4–6% negatives сохранены как отдельная история.

**V3 NONSELECTED repair/upgrade attempt; V2 r 2 остаётся experimental RFC reference; ни один не general regression-free.** Native 47-cell history и actual source/header build provenance не переименованы в V3 micro.

## 7. Литература, buffer profiles и идеи без runtime результата

[Первичная B-tree literature](../btree-novelty-20261106/PAPERS.md), [новая AM literature](../am-papers-20261107/PAPERS.md), [mechanism map](../am-papers-20261107/PAPER-MAP.md), [ideas](../am-papers-20261107/IDEAS.md). ScaleCache/OPAL/Bf-Tree/Tabular — source-backed transfer contracts и планы, **не реализованные маленькие замены buffer locking/refcounts/WAL**. ReadRecentBuffer для cached B-tree root имеет прямой PostgreSQL prior art 2023→2026; не выдаётся новой идеей. LICO — learned inverted compression, не hash-rank paper; Sphinx perfect-hash in-memory KV не является прямым доказательством ускорения hash AM.

Первый [buffer-profile gate](../btree-other-approaches-20261107/buffer-papers/RESULTS.md) завершился perf permission denied,0 samples, **SQL 1/2/4/8 тогда не запускался**. Позже root разрешил software perf; выполнен отдельный [baseline profile](../btree-next-20261107/perf/profile-summary.json):1/2/4/8 clients дали 1274/2493/4837/5859 samples. Exclusive comparison/search 14.3–19.2%,mapping 4.9–5.5%,pin/private refs 3.3–3.8%,content lock.47–.62%. Inclusive категории пересекаются, их нельзя суммировать. При 8 clients runqueue/runtime 70.8%; маленькая shared VM не доказывает many-core/NUMA contention эффекты papers. Hardware cycles/instructions/branch/cachemiss PMU **unsupported**; software stacks не являются hardware-counter evidence.

Эти этапы не противоречат друг другу: первый failed gate не выдаётся профилем, поздний успешный профиль не переписывает его историю. Неизмеренные allocation-free intarray/multirange/btree_gist, buffer/tabular идеи остаются планами, а не SQL speedups.

## 8. Что действительно остаётся полезным

1. Для upstream discussion есть содержательные маленькие кандидаты с реальным SQL gain: FTS ordered position union; большие intarray/GiST tsvector inputs с явными dispatch limits; typed V6; G1 V3/G2 V4 selective paths; H1 uniform; H2 repeated residual rescans. У каждого остаются минусы и область применения, а не «всё можно мержить».
2. Separator cache, IOS, compact state, hybrid posting search помогли разделить функциональный micro gain, вызовную частоту, representation/lifetime complexity и SQL. Для separator основной gain принадлежит typed search; array cache добавляет нестабильный бонус и устойчивый same-pivot absent штраф. Compact подтвердил memory saving, не общий SQL gain. Lazy failed-pass gain слишком редок для обещания большого COPY ускорения.
3. Rejected альтернативы — полноценный результат: MSD, word radix small inputs, CRC sampling/small radix, array typed/noinline, IOSv 4/v5/v6 частично, S1 v5,S2 v3,midpoint/Eytz/block-first остаются в каталоге. Неудачная source-fix попытка не означает исправленную SQL регрессию.
4. Ни одна формулировка «новизна» не опирается на пустой поиск. Existing PostgreSQL templates/merge/normalized pivots/Eytz/adaptive dedup/trgm GIN thread явно являются предыдущей работой. Вклад — конкретная source integration, контракты, исправления своих регрессий, production-entry fidelity, измерения и публикация отрицательных контролей.

Сопровождающий `HISTORICAL-RESULTS-20261108-sources.json` фиксирует точные размеры/SHA прочитанных первичных локальных отчётов и каталогов. Это синтез, не перезапуск старых tests/benchmarks и не переаудит каждого raw sample. Полные benchmark data/repro находятся в изначальных отдельных bundles; эта страница не заменяет их.
