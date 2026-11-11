#!/usr/bin/env python3
"""Import the reviewed finite timing protocol after ordinary qualification; do not run it."""
import hashlib
import json
import pathlib
import tarfile
import time

ROOT = pathlib.Path('/home/reshke/allfuzz/gin-dec-d2-20261111')
INPUTS = ROOT / 'inputs'
ARCHIVE = ROOT / 'timing-inputs-d2-r1.tar.gz'
ARCHIVE_SHA = 'e38697a06dd5042a4ca2006dce2ef1fb85a595718194664cd0fdb269e4c7f242'
MANIFEST_SHA = '200e76e544d0c3ce3a50565199d2ef84a6e060e7eb5787ff0c670372f211ec47'


def sha(path):
    return hashlib.sha256(pathlib.Path(path).read_bytes()).hexdigest()


def main():
    assert sha(ARCHIVE) == ARCHIVE_SHA
    assert not (ROOT / 'TIMING-IMPORT-D2-r1.json').exists()
    assert not (ROOT / 'timing-r1').exists()
    for name, expected in [
        ('BUILD-INPUTS-D2-r1.json', '11b348197ca1e912cd3616bb332a09a2780d70061e43c777aea15d25f75b30f7'),
        ('QUALIFICATION-INPUTS-D2-r1.json', '526681c089d361901c67d74a981c35674f45429d48cd864f806a432fe33a92fb'),
    ]:
        assert sha(INPUTS / name) == expected
        for relative, binding in json.loads((INPUTS / name).read_text())['files'].items():
            path = INPUTS / relative
            assert path.stat().st_size == binding['bytes'] and sha(path) == binding['sha256']
    build = json.loads((ROOT / 'build-r1/status.json').read_text())
    qualified = json.loads((ROOT / 'qualification-r1/status.json').read_text())
    assert build['status'] == 'PASS_GIN_D2_MATCHED_BUILDS'
    assert qualified['status'] == 'PASS_D2_ORDINARY_SQL_AND_VALID_DECODER'
    assert qualified['remaining_owned'] == 0 and qualified['cleanup_errors'] == []
    assert qualified['timing_samples'] == 0
    assert qualified['build_receipt_sha256'] == sha(ROOT / 'build-r1/build-receipt.json')
    for cluster in qualified['clusters']:
        assert cluster['stopped'] and not pathlib.Path(cluster['data'], 'postmaster.pid').exists()
        assert not pathlib.Path(cluster['socket'], '.s.PGSQL.' + str(cluster['port'])).exists()
        for key in ['pid', 'backend_pid']:
            assert not cluster.get(key) or not pathlib.Path('/proc', str(cluster[key])).exists()
    with tarfile.open(ARCHIVE) as stream:
        members = stream.getmembers()
        assert len(members) == 14 and len({x.name for x in members}) == 14
        data = stream.extractfile('TIMING-INPUTS-D2-r1.json').read()
        assert hashlib.sha256(data).hexdigest() == MANIFEST_SHA
        manifest = json.loads(data)
        assert {x.name for x in members} == set(manifest['files']) | {'TIMING-INPUTS-D2-r1.json'}
        contents = {}
        for member in members:
            name = pathlib.PurePosixPath(member.name)
            assert not name.is_absolute() and '..' not in name.parts
            assert member.isfile() and not member.mode & 0o7000
            assert not (INPUTS / name).exists()
            contents[member.name] = stream.extractfile(member).read()
        for name, binding in manifest['files'].items():
            assert len(contents[name]) == binding['bytes']
            assert hashlib.sha256(contents[name]).hexdigest() == binding['sha256']
        for name, content in contents.items():
            destination = INPUTS / name
            destination.parent.mkdir(parents=True, exist_ok=True)
            with destination.open('xb') as out:
                out.write(content)
    receipt = dict(status='TIMING_INPUTS_IMPORTED_NOT_LAUNCHED',
                   imported_ns=time.time_ns(), files=len(contents),
                   archive_sha256=ARCHIVE_SHA, manifest_sha256=MANIFEST_SHA,
                   build_receipt_sha256=sha(ROOT / 'build-r1/build-receipt.json'),
                   qualification_sha256=sha(ROOT / 'qualification-r1/status.json'),
                   timing_samples=0)
    (ROOT / 'TIMING-IMPORT-D2-r1.json').write_text(json.dumps(receipt, indent=2) + '\n')
    print(json.dumps(receipt, indent=2))


if __name__ == '__main__':
    main()
