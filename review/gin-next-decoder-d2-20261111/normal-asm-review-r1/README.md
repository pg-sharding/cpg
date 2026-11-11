D2 actual normal code generation

The fresh release builds use the same GCC flags and installed headers. Only ginpostinglist.o differs from B; ginget.o and ginscan.o are identical. Each selected excerpt is copied from the collected normal full-TU objdump, whose SHA and original object SHA are in REVIEW.json.

D2 tests the first byte before attempting the four-one-byte batch. When that byte has its continuation bit set, the emitted branch skips the batch input/output bounds and the remaining-byte OR and enters the scalar continuation. D1 checks batch eligibility before that scalar test. The four-byte batch and allocation/growth calls remain present. All three normal decoder frames save six registers and subtract 24 bytes from RSP (72 bytes excluding the incoming return address).

The symbol-start spans are B 592, D1 864 and D2 848 bytes, including alignment before the next symbol. They are not exact function sizes. This is an actual code-generation result, not a measured speed result. Assertion-build object equality is not applicable because its configuration differs.
