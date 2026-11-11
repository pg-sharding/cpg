#!/usr/bin/env python3
"""Copy exactly the two frozen manifests and their verified file union to new inputs/."""
import argparse
import hashlib
import json
import pathlib


def sha(data):
    return hashlib.sha256(data).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--packet', type=pathlib.Path, required=True)
    parser.add_argument('--destination', type=pathlib.Path, required=True,
                        help='New nonexistent run root; this creates its inputs/ only')
    args = parser.parse_args()
    packet = args.packet.resolve()
    destination = args.destination.resolve()
    assert not destination.exists() and not any(c.isspace() for c in str(destination))
    manifests = ['BUILD-INPUTS-K4-r1.json', 'RUNTIME-INPUTS-K4-r1.json']
    bindings = {}
    manifest_hashes = {}
    for name in manifests:
        data = (packet / name).read_bytes()
        manifest_hashes[name] = sha(data)
        for relative, binding in json.loads(data)['files'].items():
            if relative in bindings:
                assert bindings[relative] == binding
            bindings[relative] = binding
    contents = {}
    for relative, binding in bindings.items():
        name = pathlib.PurePosixPath(relative)
        assert relative == name.as_posix() and not name.is_absolute()
        assert name.parts and all(p not in {'.', '..'} for p in name.parts)
        path = packet.joinpath(*name.parts)
        assert path.is_file() and path.resolve().is_relative_to(packet)
        current = packet
        for part in name.parts:
            current = current / part
            assert not current.is_symlink()
        data = path.read_bytes()
        assert len(data) == binding['bytes'] and sha(data) == binding['sha256'], relative
        contents[relative] = data
    for name in manifests:
        assert name not in contents
        contents[name] = (packet / name).read_bytes()
    destination.mkdir(mode=0o700)
    output = destination / 'inputs'
    output.mkdir(mode=0o700)
    for relative, data in sorted(contents.items()):
        path = output / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open('xb') as stream:
            stream.write(data)
        assert path.read_bytes() == data
    assert {p.relative_to(output).as_posix() for p in output.rglob('*') if p.is_file()} == set(contents)
    receipt = dict(status='PASS_STAGED_EXACT_FROZEN_INPUT_UNION', files=len(contents),
                   manifest_sha256=manifest_hashes, destination=str(output))
    (destination / 'STAGED-INPUTS.json').write_text(json.dumps(receipt, indent=2) + '\n')
    print(json.dumps(receipt))


if __name__ == '__main__':
    main()
