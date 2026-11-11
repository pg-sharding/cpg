#!/usr/bin/env python3
"""Restore byte-exact recorded timing text from whole-line gzip chunks; no database execution."""
import argparse
import gzip
import hashlib
import json
import pathlib

HERE = pathlib.Path(__file__).resolve().parent


def digest(data):
    return hashlib.sha256(data).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--packet', type=pathlib.Path, default=HERE)
    parser.add_argument('--output', type=pathlib.Path, required=True, help='New nonexistent directory for the restored timing tree')
    args = parser.parse_args()
    packet = args.packet.resolve()
    manifest = json.loads((packet / 'recorded/timing-manifest.json').read_text())
    chunks = json.loads((packet / 'raw-chunks/MANIFEST.json').read_text())['files']
    assert manifest['status'] == 'PINNED_COMPLETE_RECORDED_TIMING_TEXT'
    args.output.mkdir()
    restored = []
    for relative, binding in manifest['files'].items():
        name = pathlib.PurePosixPath(relative)
        assert not name.is_absolute() and '..' not in name.parts
        if relative in chunks:
            parts = []
            for entry in chunks[relative]['chunks']:
                path = packet / 'raw-chunks' / entry['path']
                assert path.resolve().is_relative_to(packet / 'raw-chunks')
                compressed = path.read_bytes()
                assert digest(compressed) == entry['gzip_sha256']
                content = gzip.decompress(compressed)
                assert digest(content) == entry['uncompressed_sha256'] and len(content) == entry['uncompressed_bytes']
                assert content.endswith(b'\n') and content.count(b'\n') == entry['lines']
                parts.append(content)
            data = b''.join(parts)
        else:
            data = (packet / 'recorded/timing-r1' / name).read_bytes()
        assert len(data) == binding['bytes'] and digest(data) == binding['sha256'], relative
        path = args.output / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        restored.append(relative)
    print(json.dumps(dict(status='PASS_BYTE_EXACT_RECORDED_TIMING_RESTORATION', files=len(restored),
                          restored_jsonl_files=len(chunks), output=str(args.output))))


if __name__ == '__main__':
    main()
