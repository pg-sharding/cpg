#!/usr/bin/env python3
"""Restore original collection bytes and verify every compressed/raw SHA; no SQL."""
import argparse
import gzip
import hashlib
import json
from pathlib import Path, PurePosixPath


def digest(data):
    return hashlib.sha256(data).hexdigest()


def relative(name):
    path = PurePosixPath(name)
    assert not path.is_absolute() and '..' not in path.parts
    return Path(name)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--packet', type=Path, default=Path(__file__).resolve().parent)
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args()
    assert not a.output.exists()
    src = a.packet / 'collected'
    manifest = json.loads((src / 'COLLECTION-MANIFEST.json').read_text())
    chunks = json.loads((src / 'RAW-CHUNKS.json').read_text())['files']
    a.output.mkdir(parents=True)
    for name, expected in manifest['files'].items():
        if name in chunks:
            spec = chunks[name]
            assert spec['sha256'] == expected['sha256'] and spec['bytes'] == expected['bytes']
            pieces = []
            for part in spec['parts']:
                data = (src / relative(part['path'])).read_bytes()
                assert len(data) == part['bytes'] and digest(data) == part['sha256']
                raw = gzip.decompress(data)
                assert len(raw) == part['raw_bytes'] and digest(raw) == part['raw_sha256']
                assert raw.endswith(b'\n') and raw.count(b'\n') == part['records']
                pieces.append(raw)
            data = b''.join(pieces)
            assert data.count(b'\n') == spec['records']
        else:
            data = (src / relative(name)).read_bytes()
        assert len(data) == expected['bytes'] and digest(data) == expected['sha256'], name
        target = a.output / relative(name)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
    (a.output / 'COLLECTION-MANIFEST.json').write_bytes((src / 'COLLECTION-MANIFEST.json').read_bytes())
    print(json.dumps(dict(status='PASS_LOSSLESS_COLLECTION_RESTORE', files=len(manifest['files']),
                          chunked_files=len(chunks), new_SQL_runs=0)))


if __name__ == '__main__':
    main()
