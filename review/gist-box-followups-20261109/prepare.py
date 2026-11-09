#!/usr/bin/env python3
"""Freeze two independent BOX followups to the exact V2r2 reference."""
import difflib
import hashlib
import json
from pathlib import Path
import tarfile

ROOT = Path(__file__).resolve().parent
WORK = ROOT.parents[1]
ARCHIVE = WORK / 'review/am-experiments-20261108/hash/noop-buffer-combined-20261109/source/baseline.tar.gz'
REFERENCE = WORK / 'review/index-optimizations-20261107/parent-review-source/gist-box-batch-v2r2/src/backend/access/gist/gistget.c'
GET = 'src/backend/access/gist/gistget.c'
SCAN = 'src/backend/access/gist/gistscan.c'
HEADER = 'src/include/access/gist_private.h'
sha = lambda b: hashlib.sha256(b).hexdigest()
assert sha(ARCHIVE.read_bytes()) == '8c074fcf94a17d381e2df4a2b0554b925d76a777acb7e2f8a508abe7dfd2bbc4'
with tarfile.open(ARCHIVE) as stream:
    originals = {m.name: stream.extractfile(m).read() for m in stream if m.isfile()}
assert len(originals) == 7726
reference = REFERENCE.read_text()
assert sha(reference.encode()) == '0af264c406f4d61c8ed91011fb7ba44f46b2be9748c0350eb03909f432ea4dea'
# The reference source is separately pinned by the existing parent review.
assert reference.count('gistScanBoxItems(scan, buffer, page, tbm, ntids, maxoff)') == 1
assert 'sampleleft == 0 && sawreject' in reference

cache_get = reference.replace(
    'if (maxoff >= 2 * GIST_BOX_BATCH_SIZE &&\n\t\tgistScanBoxItems(',
    'if (maxoff >= 2 * GIST_BOX_BATCH_SIZE && so->boxBatchCandidate &&\n\t\tgistScanBoxItems(')
assert cache_get != reference
cache_scan = originals[SCAN].decode().replace(
    '#include "utils/float.h"',
    '#include "utils/float.h"\n#include "utils/fmgroids.h"\n#include "utils/fmgrprotos.h"')
anchor = '\t/* any previous xs_hitup will have been pfree\'d in context resets above */'
assert cache_scan.count(anchor) == 1
cache_scan = cache_scan.replace(anchor, '''	/*
	 * Cache only necessary caller conditions, after support functions have
	 * been copied into the scan keys.  The page helper still checks the full
	 * BOX contract and obtains the current argument on every entry.
	 */
	so->boxBatchCandidate = scan->numberOfKeys == 1 &&
		scan->numberOfOrderBys == 0 && scan->keyData[0].sk_flags == 0 &&
		scan->keyData[0].sk_func.fn_oid == F_GIST_BOX_CONSISTENT &&
		scan->keyData[0].sk_func.fn_addr == gist_box_consistent;

''' + anchor)
cache_header = originals[HEADER].decode().replace(
    '\tbool\t\tfirstCall;\t\t/* true until first gistgettuple call */',
    '\tbool\t\tfirstCall;\t\t/* true until first gistgettuple call */\n'
    '\tbool\t\tboxBatchCandidate; /* necessary BOX caller checks at rescan */')
assert cache_header != originals[HEADER].decode()

dense = reference.replace('static pg_noinline bool\ngistScanBoxItems(',
                          'static pg_noinline OffsetNumber\ngistScanBoxItems(')
begin = dense.index('static pg_noinline OffsetNumber\ngistScanBoxItems(')
end = dense.index('/*\n * Scan all items on the GiST index page', begin)
helper = dense[begin:end]
helper = helper.replace('if (query == NULL)\n\t\treturn false;',
                        'if (query == NULL)\n\t\treturn FirstOffsetNumber;')
needle = '\t\tbool\t\tsampletuple;\n\n'
assert helper.count(needle) == 1
helper = helper.replace(needle, needle + '''		/*
		 * All sampled valid BOX tuples passed their ordinary keytests.
		 * Continue at this first unprocessed offset in the generic loop;
		 * already queued/reported sample tuples must not be tested again.
		 */
		if (sampleleft == 0 && !sawreject)
			return i;

''')
assert helper.count('\treturn true;\n}') == 1
helper = helper.replace('\treturn true;\n}', '\treturn OffsetNumberNext(maxoff);\n}')
dense = dense[:begin] + helper + dense[end:]
caller = '''	if (maxoff >= 2 * GIST_BOX_BATCH_SIZE &&
		gistScanBoxItems(scan, buffer, page, tbm, ntids, maxoff))
	{
		UnlockReleaseBuffer(buffer);
		return;
	}
	for (i = FirstOffsetNumber; i <= maxoff; i = OffsetNumberNext(i))'''
replacement = '''	i = FirstOffsetNumber;
	if (maxoff >= 2 * GIST_BOX_BATCH_SIZE)
		i = gistScanBoxItems(scan, buffer, page, tbm, ntids, maxoff);
	for (; i <= maxoff; i = OffsetNumberNext(i))'''
assert dense.count(caller) == 1
dense = dense.replace(caller, replacement)
# Output routing, locking and generic iteration body remain exact reference.
generic_start = '\tfor (; i <= maxoff; i = OffsetNumberNext(i))'
old_start = '\tfor (i = FirstOffsetNumber; i <= maxoff; i = OffsetNumberNext(i))'
assert dense.split(generic_start, 1)[1] == reference[reference.index('gistScanPage(IndexScanDesc'):].split(old_start, 1)[1]

roles = {'B': {}, 'R': {GET: reference.encode()},
         'C': {GET: cache_get.encode(), SCAN: cache_scan.encode(), HEADER: cache_header.encode()},
         'D': {GET: dense.encode()}}
out = ROOT / 'source'
out.mkdir()
(out / 'base-source-files.json').write_text(json.dumps({n: {'bytes': len(b), 'sha256': sha(b)} for n,b in originals.items()}, indent=2) + '\n')
spec = {'base': '72b9498df9a369e747f8d96efb5a6cd33c2451e2', 'files': 7726,
        'reference_source_sha256': sha(reference.encode()), 'variants': {},
        'design': {'C': 'necessary caller eligibility recomputed at every rescan; full helper guards unchanged',
                   'D': 'resume the generic loop after eight valid all-pass sample tuples; no repeated outputs'},
        'relationship': 'C and D are independent alternatives above R, not a patch series'}
for role, changes in roles.items():
    folder = out / role
    folder.mkdir()
    diff = ''
    for name, data in sorted(changes.items()):
        target = folder / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
        diff += 'diff --git a/' + name + ' b/' + name + '\n'
        diff += ''.join(difflib.unified_diff(originals[name].decode().splitlines(True), data.decode().splitlines(True), fromfile='a/' + name, tofile='b/' + name))
    patch = folder / 'code.diff'
    patch.write_text(diff)
    spec['variants'][role] = {'commit': spec['base'] if role == 'B' else None,
                              'source_files': {n: {'bytes': len(b), 'sha256': sha(b)} for n,b in changes.items()},
                              'patch': {'path': role + '/code.diff', 'sha256': sha(diff.encode())}}
    if role in ('C', 'D'):
        incremental = ''
        for name, data in sorted(changes.items()):
            old = roles['R'].get(name, originals[name])
            incremental += 'diff --git a/' + name + ' b/' + name + '\n'
            incremental += ''.join(difflib.unified_diff(old.decode().splitlines(True), data.decode().splitlines(True), fromfile='a/' + name, tofile='b/' + name))
        (out / (role + '-over-V2r2.diff')).write_text(incremental)
(out / 'SOURCE.json').write_text(json.dumps(spec, indent=2) + '\n')
print(json.dumps({k:v for k,v in spec.items() if k != 'variants'}, indent=2))
