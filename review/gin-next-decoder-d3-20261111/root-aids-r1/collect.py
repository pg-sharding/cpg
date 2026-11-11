#!/usr/bin/env python3
"""Root-executed bounded collection of D3 text evidence only; no network or cluster operations."""
import argparse
import hashlib
import io
import json
import pathlib
import tarfile


def load(path):
    return json.loads(path.read_text())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=pathlib.Path, required=True)
    parser.add_argument('--stage', choices=['qualification', 'smoke', 'full'], required=True)
    parser.add_argument('--output', type=pathlib.Path, required=True, help='New archive inside this owned namespace')
    args = parser.parse_args()
    root = args.root.resolve()
    assert root.name == 'gin-dec-d3-20261111' and not args.output.exists()
    assert args.output.resolve().is_relative_to(root)
    b = load(root / 'build-r1/status.json')
    q = load(root / 'qualification-r1/status.json')
    assert b['status'] == 'PASS_GIN_D3_MATCHED_BUILDS' and b['core_cleanup_errors'] == []
    assert q['status'] == 'PASS_D3_ORDINARY_SQL_AND_VALID_DECODER'
    assert q['remaining_owned'] == 0 and q['cleanup_errors'] == [] and q['timing_samples'] == 0
    if args.stage in ['smoke', 'full']:
        s = load(root / 'timing-r1/smoke-status.json')
        assert s['status'] == 'PASS_SMOKE_NEEDS_ROOT_REVIEW' and s['remaining_owned'] == 0 and s['cleanup_errors'] == []
    if args.stage == 'full':
        s = load(root / 'timing-r1/run-status.json')
        assert s['status'] == 'PASS_FIXED_SCREEN' and (s['raw'], s['retained'], s['warm']) == (3136, 2688, 448)
        assert s['remaining_owned'] == 0 and s['cleanup_errors'] == []
    selected = set(root.glob('*.json'))
    build = root / 'build-r1'
    selected.update(build.glob('*.json'))
    selected.update(build.glob('*-normal-ASM.txt'))
    selected.update((root / 'qualification-r1').glob('*.json'))
    for role in ['B', 'D2', 'D3', 'D3_assert']:
        selected.update(root / 'qualification-r1' / role / name for name in [
            'result.json', 'decoder-raw.txt', 'boundary-raw.txt',
            'compile.log.command.json', 'link.log.command.json'])
    if args.stage in ['smoke', 'full']:
        timing = root / 'timing-r1'
        selected.update(timing.glob('*.json'))
        for stage in ['smoke'] + (['cohort0', 'cohort1'] if args.stage == 'full' else []):
            selected.update(path for path in (timing / stage).iterdir() if path.suffix in ['.json', '.jsonl'])
    files = {}
    for path in sorted(selected):
        assert path.is_file() and not path.is_symlink() and path.resolve().is_relative_to(root)
        assert path.suffix in ['.json', '.jsonl', '.txt']
        assert path.stat().st_size < 8 * 1024 * 1024
        data = path.read_bytes()
        data.decode('utf-8')
        assert b'\0' not in data and not data.startswith(b'\x7fELF')
        files[path.relative_to(root).as_posix()] = data
    tails = {}
    for pattern in ['*-core239.log', '*-postinglist-check.log']:
        for path in sorted(build.glob(pattern)):
            assert not path.is_symlink() and path.stat().st_size < 2 * 1024 * 1024
            raw = path.read_bytes()
            name = path.relative_to(root).as_posix() + '.tail.txt'
            files[name] = b''.join(raw.splitlines(keepends=True)[-80:])
            tails[name] = dict(original_bytes=len(raw), original_sha256=hashlib.sha256(raw).hexdigest(), last_lines=80)
    assert 300 < len(files) < 600 and sum(map(len, files.values())) < 64 * 1024 * 1024
    manifest = dict(status='BOUNDED_D3_TEXT_COLLECTION', stage=args.stage,
                    files={name: dict(bytes=len(data), sha256=hashlib.sha256(data).hexdigest()) for name, data in sorted(files.items())},
                    derived_test_tails=tails,
                    excluded=['PGDATA', 'ELFs', 'objects', 'shared libraries', 'full runner/build logs', 'baseline archive'])
    files['COLLECTION.json'] = (json.dumps(manifest, indent=2) + '\n').encode()
    with tarfile.open(args.output, 'x:gz') as archive:
        for name, data in sorted(files.items()):
            entry = tarfile.TarInfo(name)
            entry.mode = 0o644
            entry.size = len(data)
            archive.addfile(entry, io.BytesIO(data))
    print(json.dumps(dict(status='PASS_BOUNDED_D3_TEXT_COLLECTION', stage=args.stage,
                          files=len(files), bytes_uncompressed=sum(map(len, files.values())),
                          archive_bytes=args.output.stat().st_size,
                          archive_sha256=hashlib.sha256(args.output.read_bytes()).hexdigest())))


if __name__ == '__main__':
    main()
