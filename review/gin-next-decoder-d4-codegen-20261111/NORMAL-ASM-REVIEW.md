# D4 actual normal release codegen review

The collected isolated compile-only evidence passes independent text/receipt review. The exact D4 draft (`d01496315db5513bc64bb399f003f14be8eb9edf4d634173b1543d5285731113`) compiled as a full `ginpostinglist.c` translation unit with the same actual GCC 13.3 flags/includes as B, D2 and D3r2. No link, module load, server, backend qualification or timing ran. `PEER-CODEGEN-REVIEW-r1.json` records the independent checks and `evidence-codegen-r1/status.json` records the execution.

All fifteen command receipts and output hashes match; all four compiler outputs are empty and return success. Input source/helper/argv/header-manifest bytes match `root-codegen-r1/INPUTS.json`. The runner verifies all 907 installed server headers and the old backend SHA before and after compiling. That remote verification is attested by the inspected runner/status, not rerun by this offline review. CFLAGS include `-O2 -g -fno-lto`, CPPFLAGS are `-D_GNU_SOURCE`, and the collected object format is ELF64 x86-64.

The strongest control is exact repetition: after excluding only the leading object-file path/header, the entire B, D2 and D3 disassembly texts, including all function bytes, addresses and relocation annotations, equal their previous `decoder-d3/evidence-codegen-r2/` outputs. Their complete nm texts also match byte for byte. This is stronger than matching function sizes alone.

| Role | Decoder function bytes | Local RSP allocation | Saved registers | Decoder allocation call sites |
|---|---:|---:|---:|---:|
| B | 589 | 24 bytes | 6 / 48 bytes | 3 |
| D2 | 844 | 24 bytes | 6 / 48 bytes | 3 |
| D3r2 | 1241 | 24 bytes | 6 / 48 bytes | 4 |
| D4 | 838 | 24 bytes | 6 / 48 bytes | 3 |

D4's decoder is six bytes smaller than D2 and 403 smaller than D3r2. This is a static code-size observation, not a runtime or dynamic instruction-count result. All four save `%r15`, `%r14`, `%r13`, `%r12`, `%rbp` and `%rbx`, and the decoder has no stack-canary access. The 24-byte local frame plus saved registers is 72 bytes excluding the incoming return address; it does not describe whole-query stack use. No scalar helper symbol/reference survives. D4's only decoder relocations are one `palloc_mul` and two `repalloc_mul` call sites. Static call-site counts do not count executed allocations.

The D4 long/batch split survives compilation. In the collected decoder (start `0x1f0`), byte 0 is loaded at `0x2ff`, tested at `0x30e`, and a short value branches at `0x310` to batch eligibility at `0x290`. A long value falls through to the unrolled second-byte load at `0x316`, without taking the batch input/output bounds checks. The continuation shifts and termination decisions remain inline through byte seven.

On the short path, `0x290..0x29e` checks that three bytes remain after the consumed value, and `0x2a0..0x2aa` checks for four free output entries. Only then do `0x2ac..0x2b9` read/combine the following three continuation bits and select the batch at `0x440`. The batch advances the original input pointer by four. Rejection or completed scalar decoding reaches the common single-item emission at `0x2c0`; the common loop end at `0x2ea` returns through capacity checking to the next byte-0 decision. There is no retained per-segment scalar mode, so a later short run can batch.

D2 already loads byte 0 once (`0x293`) and tests it once (`0x2a2`) before choosing its paths. D4 therefore does not establish removal of a duplicate first-byte load or test. Its source refactor changes branch direction/layout and pointer-state handling; the actual long path now falls through and the short path branches backward to eligibility. Different code placement, branch displacements and pointer updates may help or hurt. This review makes no instruction-saving or performance attribution from them.

The D2-shaped risk remains concrete: alternating short/long values may repeatedly enter and reject batch eligibility on each short value, while D3 can stay scalar for the segment. Codegen does not prove that D4 preserves D3's homogeneous multibyte behavior or improves singleton/growth cases. The existing 21 native plus seven SQL cases and the complete valid-input gate remain pending for D4, as described in `DESIGN.md`; no new runtime campaign is part of this packet.

Limits: the packet contains disassembly/nm text and recorded object hashes, not relocatable binaries, so those whole-object hashes cannot be recomputed offline. Compiler/system-header dependency closure and the inherited environment were not fully recorded; in particular no separate environment-clearing receipt exists. The reviewed 907-header manifest is the installed server-header set, not every system header used by GCC. Exact unchanged control bytes/relocations support this bounded comparison. They do not prove valid-input behavior of D4 or a timing benefit.
