#!/usr/bin/env python3
"""Collect bounded text evidence from this experiment only, excluding PGDATA and binaries."""
import argparse
import hashlib
import io
import json
import pathlib
import re
import tarfile


def selected_timing(root, relative):
    parts = pathlib.PurePosixPath(relative)
    assert relative == parts.as_posix() and not parts.is_absolute()
    assert parts.parts and all(re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]*', p) for p in parts.parts)
    assert re.fullmatch(r'timing-r[1-9][0-9]*', parts.name)
    path = root.joinpath(*parts.parts)
    assert path.is_dir() and path.resolve().is_relative_to(root.resolve())
    current = root
    for part in parts.parts:
        current = current / part
        assert not current.is_symlink()
    return path, parts.name.removeprefix('timing-')


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--root', type=pathlib.Path, required=True)
    p.add_argument('--output', type=pathlib.Path, required=True)
    p.add_argument('--timing-name', default='timing-r1', help='Safe relative timing path, e.g. r2/timing-r2')
    a = p.parse_args()
    r = a.root.resolve()
    assert r.name == 'gin-cache-k4-20261111' and not a.output.exists()
    files = {}
    for path in r.glob('*.json'):
        files[path.relative_to(r).as_posix()] = path.read_bytes()
    build = r / 'build-r1'
    for path in build.glob('*.json'):
        files[path.relative_to(r).as_posix()] = path.read_bytes()
    for path in build.glob('*-normal-ASM.txt'):
        files[path.relative_to(r).as_posix()] = path.read_bytes()
    for pattern in ['*-core239.log', '*-postinglist-check.log', '*-layout-assert.log']:
        for path in build.glob(pattern):
            name = path.relative_to(r).as_posix() + '.tail.txt'
            files[name] = b''.join(path.read_bytes().splitlines(True)[-80:])
    q = r / 'qualification-r1'
    for path in q.glob('*.json'):
        files[path.relative_to(r).as_posix()] = path.read_bytes()
    for role in ['B', 'C', 'K3', 'K4', 'K4_assert']:
        for path in (q / role).glob('*'):
            if path.is_file() and path.suffix in {'.json', '.txt'}:
                files[path.relative_to(r).as_posix()] = path.read_bytes()
    timing, run_tag = selected_timing(r, a.timing_name)
    for path in timing.glob('*.json'):
        files[path.relative_to(r).as_posix()] = path.read_bytes()
    for name in ['smoke', 'cohort0', 'cohort1']:
        for path in (timing / name).glob('*'):
            if path.is_file() and path.suffix in {'.json', '.jsonl'}:
                files[path.relative_to(r).as_posix()] = path.read_bytes()
    assert files and sum(map(len, files.values())) < 150 * 1024 * 1024
    manifest = {name: {'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()}
                for name, data in sorted(files.items())}
    files['COLLECTION.json'] = (json.dumps(manifest, indent=2) + '\n').encode()
    with tarfile.open(a.output, 'w:gz') as tf:
        for name, data in sorted(files.items()):
            info = tarfile.TarInfo(name)
            info.mode = 0o644
            info.size = len(data)
            tf.addfile(info, io.BytesIO(data))
    print(json.dumps({'timing_name': a.timing_name, 'files': len(files), 'bytes_uncompressed': sum(map(len, files.values())),
                      'archive_bytes': a.output.stat().st_size,
                      'archive_sha256': hashlib.sha256(a.output.read_bytes()).hexdigest()}))


if __name__ == '__main__':
    main()
