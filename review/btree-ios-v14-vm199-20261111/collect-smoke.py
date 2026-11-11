#!/usr/bin/env python3
"""Export the exact finite smoke-review input list before accepting timing."""
from pathlib import Path
import hashlib
import json
import tarfile

ROOT = Path(__file__).resolve().parent
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
assert json.loads((ROOT / 'PREPARE-r1.json').read_text())['status'] == 'READY_FOR_ROOT_SMOKE_REVIEW'
paths = (ROOT / 'inputs-r1/SMOKE-COLLECT-FILES.txt').read_text().splitlines()
paths += ['PREPARE-r1.json', 'HOST-r1.json', 'CORRECTNESS-SEED-r1.json',
          'SMOKE-REVIEW-r1.json', 'create-correctness-seed.sql']
assert len(paths) == len(set(paths)) == 39
manifest = {}
for name in paths:
    p = ROOT / name
    assert p.is_file() and not p.is_symlink()
    manifest[name] = dict(bytes=p.stat().st_size, sha256=sha(p))
manifest_path = ROOT / 'SMOKE-MANIFEST-r1.json'
manifest_path.write_text(json.dumps(manifest, indent=2) + '\n')
archive = ROOT / 'smoke-evidence-r1.tar.gz'
assert not archive.exists()
with tarfile.open(archive, 'w:gz') as tar:
    for name in paths:
        tar.add(ROOT / name, arcname=name, recursive=False)
    tar.add(manifest_path, arcname='MANIFEST.json', recursive=False)
result = dict(status='PASS', files=len(manifest), bytes=archive.stat().st_size,
              archive_sha256=sha(archive), manifest_sha256=sha(manifest_path))
(ROOT / 'SMOKE-COLLECTION-r1.json').write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps(result))
