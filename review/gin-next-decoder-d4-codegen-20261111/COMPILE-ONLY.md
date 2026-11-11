# D4 normal release compile-only input

`NORMAL-RELEASE-COMPILE-ARGV.json` is command data, not an execution receipt. It reproduces the recorded normal full-TU D3r2 compile flags/includes, substituting only a fresh common source/object path under `/home/reshke/allfuzz/gin-dec-d4-codegen-only-20261111/`. The compiler is GCC 13.3; flags include `-O2 -g -fno-lto` and `-D_GNU_SOURCE`. This emits a relocatable object only. It does not link, install, load a module, start a backend or collect timings.

The historical workspace reference is `../decoder-d3/evidence-codegen-r2/D3-compile.txt.command.json`, `status.json`, compiler/flags outputs and header bindings. The packet retains the required previous disassembly/nm controls in `prior-control-codegen-r2/` and actual command/flag receipts in `evidence-codegen-r1/`. The read-only include prefix is:

```text
/home/reshke/allfuzz/gin-dec-d2-20261111/build-r1/stage-B/home/reshke/allfuzz/gin-dec-d2-20261111/build-r1/prefix
```

Root completed the check using the input capsule `root-codegen-r1/` and collected text results in `evidence-codegen-r1/`. `root-codegen-r1/root-compile-r1.py` is the actual executed helper. It matches the recorded compiler output, pg_config CFLAGS/CPPFLAGS, all 907 installed header hashes and old backend bytes before/after compilation, bounds each child to 120 seconds, uses nice 10 and a 3 GB address-space limit. It inherits the environment; no environment-clearing receipt or complete system-header dependency trace was collected. A pre-existing output/scratch namespace is not reused.

From this directory (or the assembled packet root), the exact D4 compile command can be rendered safely, without execution:

```sh
python3 - <<'PY'
import json, shlex
from pathlib import Path
p = Path('NORMAL-RELEASE-COMPILE-ARGV.json')
print(shlex.join(json.loads(p.read_text())['args']))
PY
```

The parsed argv is passed directly to `subprocess.run`, without `eval`. B, D2, D3r2 and D4 compile through the same common full-TU source/object paths and flags, saving each role's disassembly/nm/hash receipt before replacement. The references are the existing B and D2 snapshots and canonical D3r2 `1ce29c18ceb41882deced3ebe680ee75ba2c29b0`; canonical D4 is `d2866655e3b0932ce449fe8ecbf3db52404fe4f8`, with source SHA256 `d01496315db5513bc64bb399f003f14be8eb9edf4d634173b1543d5285731113`.

For a later independent compile-only replay, dependencies must already be present: Linux x86-64, Python 3.9+, GCC with the exact recorded version output, binutils `objdump`/`nm`, and an installed B prefix with identical pg_config flag output, all 907 server-header bytes and the recorded backend hash. The packet is not a toolchain or backend binary distribution. The actual helper uses `Path.is_relative_to`, resource limits and Unix nice semantics. No fetch/install occurs in it.

From the assembled packet root, stage to a new owned directory and choose the existing read-only B prefix. This snippet changes only paths and their bindings in the new copy; it does not compile:

```sh
python3 - /new/owned/d4-codegen-replay /existing/read-only/B-prefix <<'PY'
import hashlib, json, shutil, sys
from pathlib import Path
dst, prefix = Path(sys.argv[1]).resolve(), Path(sys.argv[2]).resolve()
assert not dst.exists()
shutil.copytree(Path('root-codegen-r1'), dst)
metadata = json.loads((dst / 'INPUTS.json').read_text())
old_prefix = metadata['prefix']
argv = json.loads((dst / 'ARGV.json').read_text())
argv['args'] = [a.replace('-I' + old_prefix + '/', '-I' + str(prefix) + '/')
                for a in argv['args']]
argv['args'][-3] = str(dst / 'common-source/src/backend/access/gin/ginpostinglist.c')
argv['args'][-1] = str(dst / 'common-ginpostinglist.o')
(dst / 'ARGV.json').write_text(json.dumps(argv, indent=2) + '\n')
metadata['prefix'] = str(prefix)
p = dst / 'ARGV.json'
metadata['files']['ARGV.json'] = dict(bytes=p.stat().st_size,
    sha256=hashlib.sha256(p.read_bytes()).hexdigest())
(dst / 'INPUTS.json').write_text(json.dumps(metadata, indent=2) + '\n')
PY
```

After checking those staged paths and prerequisites, the actual compile-only replay command is:

```sh
python3 -B /new/owned/d4-codegen-replay/root-compile-r1.py
```

The new `outputs-r1/` holds all fifteen command/output receipts and status. Each of four compiles uses the same new common source/object pathname. Outputs are never written into the publication packet. A replay with a different compiler/header/flag set is a separate codegen experiment and cannot claim exact reproduction of the recorded environment. The original inherited environment is unavailable for exact replay; record the replay environment explicitly when assessing differences.

For each object, retain the complete `objdump -drwC` and `nm -S --size-sort` outputs and a command/status/hash receipt. Check scalar helper calls/inlining, long-path branch placement, batching after a long delta, frame/saved-register footprint, decoder function size, and static allocation call sites. Compare D4 with D2 directly. Identical or near-identical code to D2 may leave the known D2 tradeoff unresolved. An object difference alone neither qualifies valid decoding nor proves a runtime benefit. There is no full backend/SQL/timing step in this instruction.
