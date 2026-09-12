# Boyer-Moore-Horspool for LIKE patterns: benchmark results

## Patch info

- **Patch ID:** 7013
- **Title:** Use Boyer-Moore-Horspool for simple LIKE contains patterns
- **Author:** Atsushi Ogawa
- **Version:** v2 (+721 -2 lines)
- **URL:** https://commitfest.postgresql.org/patch/7013/

## What it does

Adds a Boyer-Moore-Horspool (BMH) fast path for `LIKE '%literal%'`
(contains-search) patterns. Dispatches at execution time from textlike
and namelike. Caches prepared search state in FmrInfo.fn_extra.

Restricted to deterministic collations and single-byte or UTF-8 encodings.

## Setup

- 1M rows, 254MB table
- `text_col` = `'prefix_' || md5(id::text) || '_suffix_' || repeat('x', id % 100)`
- Sequential scan (no index used for LIKE '%...%')
- 5 runs per pattern, measuring Execution Time

## Results: main patterns

```
 Pattern                            HEAD (ms)       BMH (ms)        Speedup
─────────────────────────────────────────────────────────────────────────────
 '%abc1%' (short, 4 chars)          126-147         104-106          20-28% faster
 '%xyz789d%' (medium, 8 chars)      253-272          75- 97          63-70% faster
 '%long_pattern_string_here_12345%' 117-136         114-131          ~5-15% faster
```

## Results: pattern length sweep (best of 3 runs, ms)

```
 Pattern length   HEAD    BMH     Speedup
─────────────────────────────────────────
 1 char (%a%)      89      88      ~0%
 2 chars (%ab%)   116     116      ~0%
 3 chars (%abc%)  123     123      ~0%
 4 chars (%abcd%) 120     103      14% faster
 5 chars (%abcde%) 123     96      22% faster
 6 chars (%abcdef%) 123    78      37% faster
 7 chars (%abcdefg%) 127    89      30% faster
 8 chars (%abcdefgh%) 123    88      28% faster
 9 chars (%abcdefghi%) 125    68      46% faster
10 chars (%abcdefghij%) 125    66      47% faster
```

## Results: long strings (~500 bytes per row, 100K rows, 53MB table)

```
 Pattern                         HEAD (ms)       BMH (ms)        Verdict
─────────────────────────────────────────────────────────────────────────
 '%a%' (1 char)                   24-43           28-42          neutral
 '%ab%' (2 chars)                 51-69           54-71          neutral
 '%abc%' (3 chars)                55-77           54-75          neutral
 '%abcd%' (4 chars)              69-76           71-74          neutral
 '%abcde%' (5 chars)             56-72           56-75          neutral
 '%abcdef%' (6 chars)           57-68           74-77          neutral
 '%abcdefgh%' (8 chars)         71-74           56-73          neutral
 '%abcdefghij%' (10 chars)      54-80           56-77          neutral
 '%abcdefghijabcdefghij%' (20)  71-73           70-73          neutral
```

On long strings (~500 bytes per row), BMH shows no improvement. The
pattern is too short relative to the string length, and almost every
sliding window position contains pattern characters, so BMH skip
distances are minimal.

## Results: rare patterns (unlikely to match)

Patterns with rare character combinations that don't appear in the data:

### 1M short strings (~60 bytes per row)
```
 Pattern                        HEAD (ms)    BMH (ms)     Verdict
──────────────────────────────────────────────────────────────────
 '%zzzz%' (4 chars)              110-114      114-116     neutral
 '%zzqqzz%' (6 chars)            111-128      114-116     neutral
 '%xyzzyx%' (6 chars)           247-263      250-271      neutral
 '%abcabcabcabcabcabc%' (18)     123-141      124-128     neutral
 '%the_quick_brown_fox%' (19)    111-134      113-135     neutral
```

### 100K long strings (~500 bytes per row)
```
 Pattern                        HEAD (ms)    BMH (ms)     Verdict
──────────────────────────────────────────────────────────────────
 '%zzzz%' (4 chars)              55-82        55-74        neutral
 '%zzqqzz%' (6 chars)           56-72        71-73        neutral
 '%xyzzyx%' (6 chars)           156-173      156-175      neutral
 '%abcabcabcabcabcabc%' (18)     71-74        55-76        neutral
 '%the_quick_brown_fox%' (19)    49-73        55-73        neutral
```

No improvement for rare patterns either. The BMH implementation may not
be kicking in for these patterns, or the skip distances aren't large
enough relative to the string length to overcome the setup overhead.

## Results: 10M rows with GIN trigram index (1.6GB table)

```
 Pattern              GIN index (bitmap scan)              Seq scan (no index)
                      HEAD       BMH        delta         HEAD       BMH        delta
──────────────────────────────────────────────────────────────────────────────────
 '%abc%' (3 char)    2472-2718  2363-6065   noisy         1647-1682  1598-1674   ~3%
 '%abcde%' (5)        22- 37     23- 39      similar       1654-1690  1653-1704   ~0%
 '%abcdefgh%' (8)     0.4-0.5    0.4-0.6    similar       1634-1662  1645-1656   ~0%
 '%abcdefghij%' (10)  0.4-0.4    0.4-0.4    same          1619-1649  1630-1645   ~0%
 '%xyz789d%' (8)      0.3-0.4    0.3-0.3    same          2804-2808  2808-2876   ~0%
```

On 10M rows, GIN index is extremely effective for selective patterns
('%abcdefgh%' = 0.4ms). For non-selective patterns ('%abc%' matches ~1M
rows), GIN is slow (2.5s) because it has to recheck many rows.

BMH shows no meaningful difference with GIN index or on seq scan at
this scale. The seq scan time is dominated by I/O (1.6GB table), not
by the pattern matching algorithm.

## Conclusion

BMH is most valuable when:
- No trigram index exists (or can't be used)
- Pattern is 4+ characters long
- Sequential scan is required

With a GIN trigram index, BMH provides no additional benefit — the
index is orders of magnitude faster than any sequential scan approach.
