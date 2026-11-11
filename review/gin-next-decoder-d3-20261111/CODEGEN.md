D3 actual compile-only code generation

Root compiled complete B/D2/D3 translation units against the same actual B installed907headers, GCC13.3 and pg_config-O2-g-fno-lto flags. The old prefix/ELF/headers remained read-only. These are three normal full-TU compilations per revision, not fresh full-backend builds or performance measurements.

R1 (da951d2777e7b021966e5c9ade770bd434242e15) emits separate segment-selected loops but outlines decode_varbyte into a219byte helper. Both scalar paths call it (object offsets0x400 and0x4b5); the main frame grows from24 to56bytes and gains a canary. It is retained as a codegen-only negative; no R1 fullbuild or latency measurement is claimed.

R2 (1ce29c18ceb41882deced3ebe680ee75ba2c29b0) makes exactly one additional source-line annotation: static pg_always_inline uint64 decode_varbyte. The existing B72 macro is used, with no compiler-flag or threshold change. Actual nm/ASM show no outlined decoder symbol or call, and the main frame is24bytes again. Main function exact nm sizes are B589bytes/D2844bytes/D3r21241bytes. That larger function is a remaining risk. It does not prove instruction-cache, branch-predictor or register-pressure causes for any prior latency.

CODEGEN-COMPARISON-r1.json recounts actual collected hashes/symbols/frames; ROOT-CODEGEN-REVIEW-r1.json retains the parent's first negative review. Complete actual text ASM/nm/provenance is in evidence-codegen-r1 and evidence-codegen-r2. R1 source/codegen and all old D2 packets remain immutable. Only R2 proceeds to separately reviewed clean builds, ordinary valid-input gates and a frozen screen with all old18native+7SQL controls plus3 declared mixed cases. No speed claim exists at this preparation stage.
