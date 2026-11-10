# Installed K3 budget boundary oracle

This is a new **untimed, not yet compiled/executed** diagnostic. It does not
include production ginlogic.c, reinterpret the opaque memo, change an opclass
or replace installed callback dispatch. Build it separately against each exact
B/K1/K3/K3_assert install using that install's pg_config CFLAGS/CPPFLAGS and
server/client headers. Use the same production compiler/flags as the standard
native oracle, add -Werror -fPIC and the role macros from PROTOCOL.json, then
link -shared -fno-lto. Record source/object/module/headers/prefix/ELF hashes.

Register only in the owned private qualification cluster, replacing MODULE with
the resulting absolute library path:

```sql
CREATE FUNCTION public.gin_cache_budget_oracle(regclass,tsquery,boolean)
RETURNS text AS 'MODULE', 'gin_cache_budget_oracle' LANGUAGE C STRICT;
SELECT public.gin_cache_budget_oracle('g1.docs_d_gin'::regclass,
                                    'common'::tsquery,false);
```

Run the eleven exact queries in PROTOCOL.json against the existing ordinary
builtin tsvector GIN fixture. Persist the complete raw text durably before JSON
parsing/assertions. Require the listed expected fields, all return count sums
and cross-variant return-count equality; the single-term `one` case also has
literal FALSE/TRUE/MAYBE counts. Do not invent an execution receipt now.

Each invocation issues 1176 checked dispatch calls with both recheck sentinels.
The independent expected value is a direct native builtin callback invocation
on the same valid vector, while the actual call uses the installed
GinScanKey.triConsistentFn. Every step checks exact result/recheck and function
pointer phase. No timing API is used. The ordinary native/generic fallback/SQL
oracles remain separate and unchanged.

The helper checks continuous miss 63/64/65, repeated calls after permanent
fallback, a hit after miss 63 and a fresh 63/64 run, 96 cumulative misses each
separated by a hit, live independent keys and reset/reinitialize of the key
memory context. Hidden/nine-entry paths must retain the original dispatcher
pointer and direct fallback behavior. B/K1 do not adopt K3's budget.

The context-reset exercise follows production keyCtx reset/rebuild lifetime;
it does **not** call index_rescan or claim an actual AM rescan proof. The full
standard gate retains real repeated/prepared and lifecycle SQL checks. Relation
locks use index_open/index_close and ordinary ResourceOwner error cleanup;
per-key temporary contexts are deleted normally or by transaction cleanup.
Only valid synthetic support inputs and the owned fixture are used. Root owns
all actual compilation, import and launch approvals. No latency claim follows
from this helper.
