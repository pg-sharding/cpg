#!/usr/bin/env python3
"""Package an explicit local text collection; lossless whole-line gzip raw chunks."""
import argparse
import gzip
import hashlib
import json
from pathlib import Path, PurePosixPath
import shutil


def digest(data):
    return hashlib.sha256(data).hexdigest()


def relative(name):
    path = PurePosixPath(name)
    assert not path.is_absolute() and '..' not in path.parts
    return Path(name)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--collection', type=Path, required=True)
    p.add_argument('--allowlist', type=Path, default=Path(__file__).parent / 'RESULT-COLLECT-ALL-FILES.txt')
    p.add_argument('--output', type=Path, required=True, help='New packet collected/ directory')
    a = p.parse_args()
    assert not a.output.exists()
    names = a.allowlist.read_text().splitlines()
    assert len(names) == len(set(names)) and names
    a.output.mkdir()
    manifest, chunks = {}, {}
    for name in names:
        src = a.collection / relative(name)
        assert src.is_file() and not src.is_symlink()
        data = src.read_bytes()
        assert b'\0' not in data, 'Text collection only'
        manifest[name] = dict(bytes=len(data), sha256=digest(data))
        if name.endswith('/raw.jsonl') and len(data) > 3 * 1024 * 1024:
            assert data.endswith(b'\n')
            lines = data.splitlines(keepends=True)
            assert b''.join(lines) == data
            pieces, current = [], bytearray()
            for line in lines:
                assert line.endswith(b'\n') and line.strip()
                json.loads(line)
                if current and len(current) + len(line) > 3 * 1024 * 1024:
                    pieces.append(bytes(current))
                    current.clear()
                current.extend(line)
            if current:
                pieces.append(bytes(current))
            parts = []
            for i, raw in enumerate(pieces):
                compressed = gzip.compress(raw, compresslevel=6, mtime=0)
                assert len(compressed) < 4 * 1024 * 1024
                dest = Path('raw-chunks') / name.replace('/', '__') / ('part-%03d.jsonl.gz' % i)
                target = a.output / dest
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(compressed)
                parts.append(dict(path=dest.as_posix(), bytes=len(compressed), sha256=digest(compressed),
                                  raw_bytes=len(raw), raw_sha256=digest(raw), records=raw.count(b'\n')))
            chunks[name] = dict(**manifest[name], records=len(lines), parts=parts,
                                encoding='Concatenated decompressed whole-line chunks in listed order')
        else:
            target = a.output / relative(name)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(src, target)
    (a.output / 'COLLECTION-MANIFEST.json').write_text(json.dumps(dict(files=manifest), indent=2) + '\n')
    (a.output / 'RAW-CHUNKS.json').write_text(json.dumps(dict(files=chunks), indent=2) + '\n')
    print(json.dumps(dict(status='PASS_LOSSLESS_TEXT_COLLECTION_PACK', files=len(manifest),
                          chunked_files=len(chunks), new_SQL_runs=0)))


if __name__ == '__main__':
    main()
