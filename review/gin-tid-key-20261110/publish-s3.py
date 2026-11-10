#!/usr/bin/env python3
"""Publish explicit frozen bundles through the existing AWS CLI, with no deletes."""
import argparse
import datetime
import hashlib
import json
from pathlib import Path
import shutil
import subprocess

ROOT = Path(__file__).resolve().parent
WORKSPACE = ROOT.parents[1]
AWS = WORKSPACE / 'review/s3-upload-20261028/venv-awscli/bin/aws'
ENDPOINT = 'https://storage.yandexcloud.net'
BUCKET = 'pgtrash'
PREFIX = 'pgbugs-artifacts/'


def api(*args):
    return json.loads(subprocess.check_output([str(AWS), '--endpoint-url=' + ENDPOINT, 's3api', *args]))


def digest(path):
    content = path.read_bytes()
    return {'bytes': len(content), 'sha256': hashlib.sha256(content).hexdigest(),
            'md5': hashlib.md5(content).hexdigest()}


ap = argparse.ArgumentParser()
ap.add_argument('--bundle', action='append', required=True, help='new S3 directory=local frozen bundle')
ap.add_argument('--receipt', required=True)
args = ap.parse_args()
stage = ROOT / 's3-staging-gin-tid-key-20261110-r1'
stage.mkdir(exist_ok=True)
selected = {}
for spec in args.bundle:
    name, directory = spec.split('=', 1)
    assert name and '/' not in name and name not in ('.', '..')
    source = Path(directory).resolve()
    assert source.is_dir()
    destination = stage / name
    for f in sorted(source.rglob('*')):
        assert not f.is_symlink(), f
        if not f.is_file():
            continue
        assert f.name not in ('postmaster.pid', 'pg_control')
        relative = f.relative_to(source)
        assert '__pycache__' not in relative.parts
        target = destination / relative
        if target.exists():
            assert digest(f) == digest(target), ('changed frozen staging file', target)
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(f, target)
        selected[str(target.relative_to(stage))] = digest(target)
agents = WORKSPACE / 'AGENTS.md'
if (stage / 'AGENTS.md').exists():
    assert digest(agents) == digest(stage / 'AGENTS.md')
else:
    shutil.copy2(agents, stage / 'AGENTS.md')
selected['AGENTS.md'] = digest(stage / 'AGENTS.md')

remote = {}
names = sorted({p.split('/')[0] for p in selected if '/' in p})
for name in names:
    listing = api('list-objects-v2', '--bucket', BUCKET, '--prefix', PREFIX + name + '/')
    assert not listing.get('IsTruncated')
    for obj in listing.get('Contents', []):
        relative = obj['Key'][len(PREFIX):]
        assert relative in selected, ('unexpected preexisting object', relative)
        assert obj['Size'] == selected[relative]['bytes'], ('collision size', relative)
        if '-' not in obj['ETag']:
            assert obj['ETag'].strip('"') == selected[relative]['md5'], ('collision', relative)
        else:
            scratch = ROOT / 's3-preexisting-check.tmp'
            api('get-object', '--bucket', BUCKET, '--key', PREFIX + relative, str(scratch))
            assert digest(scratch) == selected[relative], ('collision contents', relative)
            scratch.unlink()
head = api('head-object', '--bucket', BUCKET, '--key', PREFIX + 'AGENTS.md')
assert head['ContentLength'] == selected['AGENTS.md']['bytes'] and head['ETag'].strip('"') == selected['AGENTS.md']['md5'], 'AGENTS collision'
subprocess.run([str(AWS), '--endpoint-url=' + ENDPOINT, 's3', 'sync', str(stage),
                's3://' + BUCKET + '/' + PREFIX, '--only-show-errors'], check=True)
for name in names:
    listing = api('list-objects-v2', '--bucket', BUCKET, '--prefix', PREFIX + name + '/')
    assert not listing.get('IsTruncated')
    for obj in listing.get('Contents', []):
        remote[obj['Key'][len(PREFIX):]] = obj
head = api('head-object', '--bucket', BUCKET, '--key', PREFIX + 'AGENTS.md')
remote['AGENTS.md'] = {'Size': head['ContentLength'], 'ETag': head['ETag']}
for relative, meta in selected.items():
    obj = remote[relative]
    assert obj['Size'] == meta['bytes'], ('upload size mismatch', relative)
    if '-' not in obj['ETag']:
        assert obj['ETag'].strip('"') == meta['md5'], ('upload mismatch', relative)
        meta['verified_by'] = 'size and MD5/ETag'
    else:
        scratch = ROOT / 's3-upload-check.tmp'
        api('get-object', '--bucket', BUCKET, '--key', PREFIX + relative, str(scratch))
        assert digest(scratch) == meta, ('upload downloaded contents mismatch', relative)
        scratch.unlink()
        meta['verified_by'] = 'size and downloaded full SHA256/MD5 (multipart object)'
totals = api('list-objects-v2', '--bucket', BUCKET, '--prefix', PREFIX,
             '--query', '{objects:length(Contents),bytes:sum(Contents[].Size)}')
receipt = {'status': 'PASS', 'utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
           'destination': 's3://' + BUCKET + '/' + PREFIX, 'files_verified': len(selected),
           'bytes_verified': sum(x['bytes'] for x in selected.values()),
           'method': 'size and MD5/ETag per single-part object; full downloaded SHA256/MD5 for multipart; no --delete',
           'actual_bucket_prefix_totals': totals, 'files': selected}
(ROOT / args.receipt).write_text(json.dumps(receipt, indent=2) + '\n')
print(json.dumps({k: v for k, v in receipt.items() if k != 'files'}))
