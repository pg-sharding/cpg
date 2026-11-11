#!/usr/bin/env python3
"""Write or verify a complete local assembly manifest; no copying, runtime or publication."""
import argparse
import hashlib
import json
import pathlib
import time


def inventory(root, exclude):
    result = {}
    for path in sorted(root.rglob('*')):
        assert not path.is_symlink(), ('Symlink is not a portable artifact', str(path))
        if not path.is_file() or path.resolve() == exclude:
            continue
        relative = path.relative_to(root)
        assert not set(relative.parts) & {'.git', '.aws', '__pycache__', 'pg_wal', 'pg_xact', 'pg_tblspc'}
        assert path.name not in {'PG_VERSION', 'postmaster.pid', 'postmaster.opts'}
        assert path.suffix not in {'.o', '.so', '.a', '.dylib', '.pyc', '.exe', '.tar', '.log'}
        assert not path.name.endswith(('.tar.gz', '.tgz', '.zip'))
        data = path.read_bytes()
        assert len(data) <= 32 * 1024 * 1024
        assert not data.startswith((b'\x7fELF', b'!<arch>\n', b'MZ', b'\xcf\xfa\xed\xfe', b'\xfe\xed\xfa\xcf'))
        if data.startswith(b'\x1f\x8b'):
            assert 'raw-chunks' in relative.parts or path.name.endswith('.jsonl.gz'), relative
        else:
            data.decode('utf-8')
            assert b'\0' not in data, relative
        result[relative.as_posix()] = dict(bytes=len(data), sha256=hashlib.sha256(data).hexdigest(),
                                           md5=hashlib.md5(data).hexdigest())
    assert result and sum(value['bytes'] for value in result.values()) < 128 * 1024 * 1024
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--stage', type=pathlib.Path, required=True, help='Already assembled packet, read-only except the new manifest')
    parser.add_argument('--output', type=pathlib.Path, required=True, help='Manifest path inside the stage; only this exact file is excluded')
    parser.add_argument('--verify', action='store_true', help='Verify an existing manifest without writing anything')
    args = parser.parse_args()
    root = args.stage.resolve()
    output = args.output.resolve()
    assert root.is_dir() and output.is_relative_to(root)
    assert output.suffix == '.json'
    if args.verify:
        expected = json.loads(output.read_text())
        assert expected['status'] == 'ASSEMBLED_NOT_FROZEN'
        actual = inventory(root, output)
        assert actual == expected['files']
        assert len(actual) == expected['file_count']
        assert sum(value['bytes'] for value in actual.values()) == expected['bytes']
        print(json.dumps(dict(status='PASS_COMPLETE_ASSEMBLY_FILE_HASHES', files=len(actual),
                              manifest_sha256=hashlib.sha256(output.read_bytes()).hexdigest())))
        return
    assert not output.exists()
    files = inventory(root, output)
    receipt = dict(status='ASSEMBLED_NOT_FROZEN', written_ns=time.time_ns(),
                   file_count=len(files), bytes=sum(value['bytes'] for value in files.values()),
                   excluded_only=output.relative_to(root).as_posix(), files=files,
                   scope='Hash coverage and bounded artifact-type checks only; no build, correctness, timing, approval or publication claim.')
    with output.open('x') as stream:
        stream.write(json.dumps(receipt, indent=2) + '\n')
    print(json.dumps(dict(status=receipt['status'], files=len(files), bytes=receipt['bytes'],
                          manifest_sha256=hashlib.sha256(output.read_bytes()).hexdigest())))


if __name__ == '__main__':
    main()
