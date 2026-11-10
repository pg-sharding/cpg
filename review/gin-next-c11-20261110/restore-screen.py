#!/usr/bin/env python3
"""Restore the exact collected C11 evidence into a new directory, offline."""
import argparse
import gzip
import hashlib
import json
import os
import pathlib
import shutil

ROOT = pathlib.Path(__file__).resolve().parent


def digest(data):
    return hashlib.sha256(data).hexdigest()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--packet', type=pathlib.Path, default=ROOT)
    p.add_argument('--output-new', type=pathlib.Path, required=True)
    a = p.parse_args()
    a.output_new.mkdir()
    source = a.packet / 'screen-evidence-r1'
    for path in sorted(source.rglob('*')):
        assert not path.is_symlink()
        if path.is_file():
            target = a.output_new / path.relative_to(source)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(path, target)
    raw_manifest = json.loads((a.packet / 'raw-chunks/MANIFEST.json').read_text())
    for relative, item in raw_manifest['raw_files'].items():
        name = pathlib.PurePosixPath(relative)
        assert not name.is_absolute() and '..' not in name.parts
        target = a.output_new / name
        assert not target.exists()
        target.parent.mkdir(parents=True, exist_ok=True)
        count = 0
        with target.open('xb') as stream:
            for chunk in item['chunks']:
                path = a.packet / 'raw-chunks' / chunk['name']
                blob = path.read_bytes()
                assert digest(blob) == chunk['compressed_sha256']
                data = gzip.decompress(blob)
                assert len(data) == chunk['raw_bytes'] and digest(data) == chunk['raw_sha256']
                assert data.endswith(b'\n') and data.count(b'\n') == chunk['lines']
                count += chunk['lines']
                stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        data = target.read_bytes()
        assert count == item['lines'] and len(data) == item['bytes'] and digest(data) == item['sha256']
    original = json.loads((a.output_new / 'SCREEN-EVIDENCE-r1-MANIFEST.json').read_text())
    for relative, item in original.items():
        path = a.output_new / relative
        data = path.read_bytes()
        assert len(data) == item['bytes'] and digest(data) == item['sha256'], relative
    print(json.dumps(dict(status='PASS_EXACT_OFFLINE_COLLECTION_RESTORE', files=len(original),
                          raw_files=len(raw_manifest['raw_files']),
                          scope='Offline restoration only; no PostgreSQL build, server or timing was executed.')))


if __name__ == '__main__':
    main()
