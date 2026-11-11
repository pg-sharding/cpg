# D2: leading-continuation guard, source-only alternative

D2 is not compiled, qualified or timed. It inherits D1's four-item one-byte
batch, but tests `ptr[0] & 0x80` first. A known multi-byte leading delta takes
the unchanged scalar path without evaluating the four-item bounds or the
remaining-byte OR in the C expression. This is a concrete cost hypothesis,
not an established compiler/codegen behavior or a measured fix.

The motivation is the completed, preserved D1 shared-load diagnostic: inner
allocation/materialization/free CPU regressed +38.60%/+41.31% for delta2,
+18.80%/+18.78% for delta3 and +19.03%/+18.44% for delta4, while the intended
one-byte batches improved. Exact-twin paired medians were small in those cells;
other unchanged paths also moved. These outcomes remain D1's results. D2 has no
new performance observation and does not replace, trim or relabel D1 evidence.

The outer `while (ptr < endptr)` proves that the first byte exists. After its
continuation bit is clear, the existing `endptr - ptr >= 4` and
`nallocated - ndecoded >= 4` guards still precede reads of bytes 1..3 and all
four output stores. Checking just the remaining three continuation bits is
logically equivalent to the original four-byte OR after the first bit check.
For any valid input, the same four-item batch or the same scalar fallback is
chosen. Scalar varbyte advancement, segment stepping/first-item handling,
allocation/growth/copies, TID ordering, output capacity, format and API remain
unchanged. The fixed batch width is still four.

The compiler may lay out/hoist/combine these tests in ways that defeat the cost
hypothesis, or add overhead on short/one-byte paths. Actual-header production
compiles, normal/assert codegen inspection, the same eighteen valid decoder
oracles, and all long/short/segment-growth/inline/absent/OR/full/dense/Seq
negatives are required before a latency claim. Actual decoder timing must still
include allocation/materialization/free, with compression/full output oracle
outside its inner clock. No new output sizing or upstream CF7352 work is used.
No builds or profiles may overlap K1's screen; parent review controls any later
finite build/gate/timing attempt.

The standalone commit has fixed B as its parent and is root <localhost>
authored/committed. D2-over-fixed-B.diff and D2-over-fixed-B-root.patch are an
independent alternative to D1, not a patch series. D2-over-D1-review.diff is only
the small review delta against canonical D1. Source was written once in the
new snapshot; an external Git index created the standalone tree without
changing the original object repository or this clone's HEAD/worktree. Future
ports, if approved, use real cherry-picks of that canonical commit.
