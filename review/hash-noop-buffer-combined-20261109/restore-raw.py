#!/usr/bin/env python3
"""Restore the explicit result collection from lossless transport chunks."""
import argparse
import hashlib
import json
import pathlib

HERE = pathlib.Path(__file__).resolve().parent


def digest(data):
    return hashlib.sha256(data).hexdigest()


def relative(name):
    p = pathlib.PurePosixPath(name)
    assert not p.is_absolute() and '..' not in p.parts
    return pathlib.Path(name)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--packet', type=pathlib.Path, default=HERE)
    p.add_argument('--output', type=pathlib.Path, required=True)
    a = p.parse_args()
    src = a.packet.resolve() / 'collected'
    assert not a.output.exists()
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
                pieces.append(data)
            data = b''.join(pieces)
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
