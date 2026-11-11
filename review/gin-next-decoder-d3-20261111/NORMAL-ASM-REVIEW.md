# Actual D3 release codegen review

The normal object disassembly from the fresh full backend builds matches the previously reviewed r2 function machine bytes for B, D2 and D3. No `decode_varbyte` symbol or call remains. The D3 segment classification and separate scalar/batch paths survived the full build.

| Role | Decoder function bytes | Local RSP allocation | Saved registers | Static allocation/growth call sites |
|---|---:|---:|---:|---:|
| B | 589 | 24 bytes | 6 / 48 bytes | 3 |
| D2 | 844 | 24 bytes | 6 / 48 bytes | 3 |
| D3 | 1241 | 24 bytes | 6 / 48 bytes | 4 |

All three save the same six registers and use two stack slots for persistent arguments. There is no new stack canary in this function. The local allocation is 24 bytes; saved registers add 48 bytes, for 72 additional stack bytes excluding the incoming return address. This is not a claim about whole-query stack use.

D3 is 397 bytes (+47.04%) larger than D2 and 652 bytes (+110.70%) larger than B. It has one additional static growth-call site because the scalar path is separate; this does not show extra allocations per executed command. Registers are reassigned, but the collected function has no additional stack allocation or persistent argument spill slots.

The unresolved performance risks remain: an early multi-byte delta selects scalar decoding for the rest of its segment, losing possible late dense batching; a dense-first mixed segment retains D2 dispatch costs. The declared mixed cases measure both directions and alternating deltas. No timing or speed conclusion is inferred from this review.

The r1 experiment is retained as a codegen-only negative: helper outlining introduced scalar helper calls and a 56-byte local frame. It was not built or timed as a full backend. The r2 `pg_always_inline` annotation removed that specific overhead; the code-size tradeoff remains.

D3_assert is excluded from release codegen/object equality comparisons because it uses assertion flags. The independent ordinary gate covers its behavior.

Bindings and exact call-site addresses are in `PEER-NORMAL-ASM-REVIEW-r1.json`; source/headers/ELF/core/posting and ordinary SQL/native recount are in `PEER-BUILD-QUALIFICATION-AUDIT-r4.json`.
