# Первичные источники и границы проверки

Срез: 2026-11-11 около06:17 UTC. Полный список **60+22 Message-ID с датами и URL**, все **64+15 attachment hashes/paths**, параметры archive и Git ancestry — [SOURCE-AUDIT.json](SOURCE-AUDIT.json). Здесь указаны ключевые точки аргументации, без перепубликации полного почтового корпуса.

## Основной тред

| Дата UTC | Источник | Для чего нужен |
|---|---|---|
| 2026-01-05 15:01:44 | [David, исходная серия](https://www.postgresql.org/message-id/5d366878-2007-4d31-861e-19294b7a583b%40gmail.com) | Состав v1, данные и fastest-of-three методика |
| 2026-01-06 17:00:23 | [Heikki, review](https://www.postgresql.org/message-id/9ac3931a-180e-4283-a7a8-05eb66099206%40iki.fi) | NULL result check, неверное sorted предположение, locale caveat |
| 2026-01-09 12:06:42 | [David, v2 и раздельные дельты](https://www.postgresql.org/message-id/e5dd01c6-c469-405d-aea2-feca0b2dc34d%40gmail.com) | Regression skip-sort; явный output flag; Turkish casing |
| 2026-01-09 18:36:26 | [Heikki, NULL dedup и первый commit](https://www.postgresql.org/message-id/6d16b6bd-a1ff-4469-aefb-a1c8274e561a%40iki.fi) | Альтернативная NULL обработка; inline committed |
| 2026-01-14 12:27:05 | [David, v3](https://www.postgresql.org/message-id/8a311d7b-9101-4947-a700-6a7821678462%40gmail.com) | Call-info optimization снята, новый NULL/template вариант |
| 2026-03-02 12:17:56 | [David, v4](https://www.postgresql.org/message-id/a90ebbbd-0d77-49c7-b222-3dbffa4e3b14%40gmail.com) | ASCII fast path исключён |
| 2026-04-07 11:27:40 | [Heikki, April commits](https://www.postgresql.org/message-id/6439c655-e281-409d-b884-6586750d5820%40iki.fi) | Два sort/dedup SHA и comparator reservations |
| 2026-04-22 21:26:56 | [David, v7 accumulator](https://www.postgresql.org/message-id/10395cb6-a804-49ac-b2f1-3f98d7204359%40gmail.com) | Lookup/hash strategy, memory/size changes, build profile |
| 2026-09-08 14:58:04 | [Matthias, review](https://www.postgresql.org/message-id/CAEze2WgC_LyuWG3onT5h7oz%3DrzDbvGEO_95wMu%3Dz2671kCh%2BWQ%40mail.gmail.com) | Unsigned radix, temporary memory, key-copy issue |
| 2026-09-09 08:49:05 | [David, v10](https://www.postgresql.org/message-id/1c90691c-db53-420a-be6c-e0323e6ae9f1%40gmail.com) | Copy only on !found, signedness/codegen rationale |
| 2026-09-14 12:31:23 | [David, MSD negative и v11](https://www.postgresql.org/message-id/10afd923-38f4-451c-af89-34f8654533cb%40googlemail.com) | Ранний in-place prototype; unique/copy trials; future 32-bit representation |
| 2026-10-23 07:53:26 | [David, rebased v11](https://www.postgresql.org/message-id/25e5a1da-44c9-427a-b9f9-65aac16d9a30%40gmail.com) | Последняя архивная версия |
| 2026-11-05 11:58:24 | [Heikki, comparator committed](https://www.postgresql.org/message-id/df6a9bed-14b1-4540-b88d-0f3f47b3e9c3%40iki.fi) | Integer comparator merged |
| 2026-11-05 13:28:39 | [Heikki, radix review](https://www.postgresql.org/message-id/2cb613f1-37d7-4283-b2ad-3afff466134c%40iki.fi) | Tiny arrays, fallback, memory/unique-copy proposals |
| 2026-11-09 15:31:31 | [David, v12](https://www.postgresql.org/message-id/b53f3df9-d584-47e4-a1dd-405dd8146e27%40gmail.com) | Новые alternatives и CREATE INDEX таблица |
| 2026-11-09 21:10:41 | [Kirill, numeric-array negative](https://www.postgresql.org/message-id/CALdSSPj0amESJpj0FYoruotCOHAQf6UeJyb_JsyKAe2n98gdrQ%40mail.gmail.com) | Image versus semantic equality, measured build/size effect |
| 2026-11-10 03:01:07 | [Kirill, long-key negative](https://www.postgresql.org/message-id/CALdSSPjKLKxz3_QAJJwgtSLCC6oRFcdis2bP-EXcNqoT%3DbcZQg%40mail.gmail.com) | Public profiling evidence; printed timing-arrow direction is ambiguous |
| 2026-11-10 08:37:03 | [David, semantic merging response](https://www.postgresql.org/message-id/40df4dbe-5fbb-4a7c-b0b7-34422d03e4f6%40gmail.com) | Where duplicates merge and possible remedies; no final fix attached |
| 2026-11-10 11:01:43 | [David, final observed reply](https://www.postgresql.org/message-id/352ae0e6-4aa8-483e-9aa9-01d4a4e2bdf8%40gmail.com) | Long-key hash cost and workload with opposite result |

Current [whole main thread](https://www.postgresql.org/message-id/flat/5d366878-2007-4d31-861e-19294b7a583b%40gmail.com) downloaded directly contains60 messages; web-tool cached flat snapshot lagged. Archive export was re-read after schema inspection with READ ONLY/30s/LIMIT. Direct reply search outside topic53025 returned0 rows in the archive; that is a bound on this snapshot, not global absence of continuation. Function-name search also found2012 redundant-dedup discussion and commit notices; no novelty inference rests on an empty subject query.

## v12 attachments: all published 2026-11-09 15:31:31 UTC

| Attachment | SHA256 of downloaded bytes |
|---|---|
| [0001 accumulator](https://www.postgresql.org/message-id/attachment/208606/v12-0001-Replace-GIN-build-accumulator-RB-tree-with-a-has.patch) | `e5caf39c8512bcebcef4f507bfe5a497ea11f51871aa2f1b417527fe00122dc8` |
| [0002 trigram comparator](https://www.postgresql.org/message-id/attachment/208605/v12-0002-Optimize-trigram-sort-comparators.patch) | `32769fefb01cd8254ada1b530682dbde8c2e9fa916e386bcc49b1cf5ee0344c4` |
| [0003 out-of-place LSD](https://www.postgresql.org/message-id/attachment/208604/v12-0003-Use-out-of-place-radix-sort-to-extract-trigrams.patch) | `6758318e93d9482e081b1631339bd478042face547bf414f76382ca8acc97655` |
| [0004 in-place MSD alternative](https://www.postgresql.org/message-id/attachment/208603/v12-0004-Use-in-place-American-Flag-Sort-to-extract-trigr.patch) | `fecb1b0cc46d2da0c07db7e179d5bea371cb983f0ba0e2731c6be4608c0e37d0` |
| [gin_benchmark.sql](https://www.postgresql.org/message-id/attachment/208607/gin_benchmark.sql) | `e7e30e04126858626717b23f88f374dc1590ca246790bbcab57078e5dd2944d2` |

Header author dates, including November2025 dates, are not mailing dates. Source hunks were read locally as text; attachment code/SQL was not executed.

## Explicit continuation and older scan prior art

| Date UTC | Source | Relevance |
|---|---|---|
| 2026-01-21 15:36:18 | [Collation thread](https://www.postgresql.org/message-id/db087c3e-230e-4119-8a03-8b5d74956bc2%40gmail.com) | Explicit offshoot from casing issue |
| 2026-03-26 18:26:43 | [Tom, exact index answers](https://www.postgresql.org/message-id/1017962.1774549603%40sss.pgh.pa.us) | LIKE/regex consistency and matching collation |
| 2026-10-23 08:18:31 | [Collation v8](https://www.postgresql.org/message-id/28dcdcfe-a8e2-4619-8514-a0216715d510%40gmail.com) | Latest attached pair |
| 2026-11-06 22:17:38 | [Zsolt, mixed-collation negative](https://www.postgresql.org/message-id/CAN4CZFN5dvVe1a5iB_jJYGazL%3DQzMpUmFXn6bMi2g3zmSX9PdA%40mail.gmail.com) | Latest observed continuation; fetched directly because web cache missed |
| 2014-02-06 11:36:44 | [Heikki, Small GIN optimizations](https://www.postgresql.org/message-id/52F373CC.4050800%40vmware.com) | Direct previous proposals: logical TID, heap/shared-entry warning, consistent cache, deferred decode |

## Git and CommitFest status

Observed live11 November: [CF6418](https://commitfest.postgresql.org/patch/6418/) v12/4 patches, Ready for Committer/target20; [CF6454](https://commitfest.postgresql.org/patch/6454/) v8/2 patches, Ready for Committer/target field19, latest email6 November. CF state is per entry and does not settle reported negatives or imply all pieces are merged.

Primary upstream commits, all rechecked as ancestors of B72 in the read-only local object repo:

- 2026-01-09: [bba81f9d3d4f512280bd55751a450dac6f02d406](https://github.com/postgres/postgres/commit/bba81f9d3d4f512280bd55751a450dac6f02d406).
- 2026-04-07: [6f5ad00ab763f9e029ec591f7f650bd09c1e933f](https://github.com/postgres/postgres/commit/6f5ad00ab763f9e029ec591f7f650bd09c1e933f).
- 2026-04-07: [9f3755ea07aa8858999bdac3d33151e93d2643e2](https://github.com/postgres/postgres/commit/9f3755ea07aa8858999bdac3d33151e93d2643e2).
- 2026-11-05: [41467b1d88303fbaea4ddd20c21ac4b8ce6b92d7](https://github.com/postgres/postgres/commit/41467b1d88303fbaea4ddd20c21ac4b8ce6b92d7).

Fresh official GitHub API [master metadata](https://api.github.com/repos/postgres/postgres/commits/master) gave `c5daeb1e0f5adfbc19ed621bb97ce2d68c8455bf`, committer date2026-11-11T03:14:26Z. Re-downloaded by that immutable SHA: [ginbulk.c](https://raw.githubusercontent.com/postgres/postgres/c5daeb1e0f5adfbc19ed621bb97ce2d68c8455bf/src/backend/access/gin/ginbulk.c), [trgm_op.c](https://raw.githubusercontent.com/postgres/postgres/c5daeb1e0f5adfbc19ed621bb97ce2d68c8455bf/contrib/pg_trgm/trgm_op.c). They still contain RB-tree and old trigram comparator/templated qsort respectively. Local repository HEAD remains `a6bd60dd53fb561c74fe13e7e1edaa94dd4605b7`.

Our comparison inputs are immutable local patches in Heap natural-plan publication-r1, K3 canonical source, C9/C10/C11, S1/D1/D2 and the old word-typed patch. This review creates no new benchmark evidence. Full downloaded email bodies/upstream patches stay in private temporary files; only our analysis and compact metadata are included here.
