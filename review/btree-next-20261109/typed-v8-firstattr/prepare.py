#!/usr/bin/env python3
"""Prepare a pinned V6 alternative; never modify any historical source packet."""
import difflib
import hashlib
import json
from pathlib import Path
import tarfile

ROOT = Path(__file__).resolve().parent
REVIEW = ROOT.parents[1]
PATH = 'src/backend/access/nbtree/nbtsearch.c'
PARENT = REVIEW / 'index-optimizations-followups-20261108/typed-leaf-v7/full-sql-20261108-r1/inputs/v6-nbtsearch.c'
ARCHIVE = REVIEW / 'am-experiments-20261108/hash/noop-buffer-combined-20261109/source/baseline.tar.gz'
sha = lambda data: hashlib.sha256(data).hexdigest()

assert sha(ARCHIVE.read_bytes()) == '8c074fcf94a17d381e2df4a2b0554b925d76a777acb7e2f8a508abe7dfd2bbc4'
with tarfile.open(ARCHIVE) as archive:
    member, = [m for m in archive.getmembers() if m.name.endswith(PATH)]
    baseline = archive.extractfile(member).read().decode()
parent = PARENT.read_text()
assert sha(parent.encode()) == '681db606e5285bacc18faf073dca9ae1adb8e0a8396ccf96a9c56fdfbf88048f'
old = '''		int64 value = 0;
		bool isnull;
		int32 result;

		{
			IndexTuple itup = (IndexTuple) PageGetItem(page,
												PageGetItemId(page, mid));
			Datum datum;

			if (BTreeTupleGetNAtts(itup, rel) != 1)
			{
				result = _bt_compare(rel, key, page, mid);
				goto compared;
			}
			datum = index_getattr(itup, 1, RelationGetDescr(rel), &isnull);
			if (!isnull)
				value = DatumGetInt64(datum);
		}
		if (isnull || (!leaf && value == argument))'''
new = '''		int64 value;
		int32 result;

		{
			IndexTuple itup = (IndexTuple) PageGetItem(page,
												PageGetItemId(page, mid));

			if (BTreeTupleGetNAtts(itup, rel) != 1 ||
				IndexTupleHasNulls(itup))
			{
				result = _bt_compare(rel, key, page, mid);
				goto compared;
			}

			/*
			 * Eligibility guarantees one int8 attribute.  Without a null
			 * bitmap, its bytes start immediately after the aligned header.
			 * Avoid descriptor/cache-offset and Datum representation checks
			 * for every comparison; memcpy also works without an aligned load.
			 */
			memcpy(&value, (char *) itup + MAXALIGN(sizeof(IndexTupleData)),
				   sizeof(value));
		}
		if (!leaf && value == argument)'''
assert parent.count(old) == 1
candidate = parent.replace(old, new)
prefix, suffix = parent.split(old)
assert candidate == prefix + new + suffix
assert candidate[candidate.index('/* Typed read searches'): ] == parent[parent.index('/* Typed read searches'): ]

def write_new(name, data):
    path = ROOT / name
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x') as stream:
        stream.write(data)

def diff(before, after):
    return 'diff --git a/' + PATH + ' b/' + PATH + '\n' + ''.join(
        difflib.unified_diff(before.splitlines(True), after.splitlines(True),
                             fromfile='a/' + PATH, tofile='b/' + PATH))

sources = {'B72': baseline, 'V6': parent, 'V8': candidate}
for role, source in sources.items():
    write_new('source/' + role + '/nbtsearch.c', source)
write_new('typed-v8-firstattr.diff', diff(baseline, candidate))
write_new('v6-to-v8-firstattr.diff', diff(parent, candidate))
receipt = {
    'status': 'SOURCE_ONLY', 'base_revision': '72b9498df9a369e747f8d96efb5a6cd33c2451e2',
    'parent_commit': 'a37f4cd9798b21ad97edab4a71d452bbc7641c1c',
    'parent_input': str(PARENT.relative_to(REVIEW.parent)),
    'path': PATH, 'source_sha256': {r: sha(s.encode()) for r, s in sources.items()},
    'unchanged': ['eligibility predicate', 'generic/write descent', 'typed internal descent',
                  'internal equality fallback', 'assert same-page offset oracle'],
    'changed': 'nonnull single-attribute int8 payload load inside the typed comparator only',
    'runtime_results': None,
}
write_new('SOURCE.json', json.dumps(receipt, indent=2) + '\n')
print(json.dumps(receipt, indent=2))
