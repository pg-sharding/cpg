"""Freeze the completed continuation index after all three publications verify."""
import datetime
import hashlib
import json
import pathlib
import shutil

ROOT = pathlib.Path(__file__).resolve().parent
OUT = ROOT / 'continuation-overview-publication-r1'
assert not OUT.exists()
names = ['HEAP-NATURAL-SQL', 'HEAP-SHORT-BATCH-SQL', 'K3-DISPATCH']
receipts = {}
for name in names:
    result = json.loads((ROOT / (name + '-RESULTS-GIT-r1.json')).read_text())
    upload = json.loads((ROOT / (name + '-S3-RECEIPT-r1.json')).read_text())
    remote = json.loads((ROOT / (name + '-REMOTE-VERIFIED-r1.json')).read_text())
    assert result['status'] == 'PUSHED_REMOTE_REF_VERIFIED'
    assert upload['status'] == 'PASS'
    assert remote['refs'][result['branch']] == result['commit']
    receipts[name] = result
for relative, expected in [
    ('heap-selective-natural-20261110/ROOT-FINAL-LIVE-r1.json', 9),
    ('heap-short-batch-20261111/ROOT-FINAL-LIVE-r1.json', 9),
    ('k3-dispatch-diagnostic-20261110/ROOT-FINAL-LIVE-DIAG-r2.json', 3),
]:
    proof = json.loads((ROOT / relative).read_text())
    assert proof['status'].startswith('PASS')
    assert proof.get('stopped_cluster_lifetimes', proof.get('stopped_clusters')) == expected
OUT.mkdir()
for name in ['GIN-CONTINUATION-RESULTS-20261111.md', 'WAVE-RESULTS.md', 'CONTINUATION-r2.md',
             'K3-DISPATCH-SOURCE-REMOTE-VERIFIED-r1.json', 'prepare-continuation-overview-r1.py']:
    shutil.copy2(ROOT / name, OUT / name)
for name in names:
    for suffix in ['RESULTS-GIT-r1.json', 'S3-RECEIPT-r1.json', 'REMOTE-VERIFIED-r1.json']:
        shutil.copy2(ROOT / (name + '-' + suffix), OUT / (name + '-' + suffix))
links = {name: 'https://github.com/pg-sharding/cpg/tree/' + value['commit'] + '/' + value['git_prefix']
         for name, value in receipts.items()}
intro = ('# Completed GIN continuation index\n\n'
         'Read GIN-CONTINUATION-RESULTS-20261111.md for the new results and limits; '
         'WAVE-RESULTS.md preserves the wider experiment history. All three complete '
         'packets below contain patches, unsent English drafts, exact input/setup/build '
         'instructions, actual evidence and independent replay/audit tools. This index '
         'does not duplicate their payloads. Alternatives are not a patch series.\n\n')
for name, link in links.items():
    intro += '- [' + name + '](' + link + ')\n'
intro += ('\nAll 21 SQL/diagnostic lifetimes have final live stop and binding proofs. '
          'New numbers use historical fixed B72. K3 instrumentation has no latency '
          'comparison; its old dense regression remains unresolved. Earlier single-scan '
          'negatives remain immutable. Fresh portable frontdoors were locally checked '
          'only; actual historical build/run controllers executed on the VMs.\n')
(OUT / 'README.md').write_text(intro)
draft = ('UNSENT OVERVIEW DRAFT\nSubject: GIN heap SQL follow-ups and dispatcher observations\n\n'
         'The unchanged required-entry heap prototype reduces natural GIN OR32/OR128 '
         'executor time by about 10–11% in two fixed-B72 cohorts. Short single-query '
         'negatives and exact-twin variation remain. A separate 100-rescan command '
         'experiment gives OR8 about 4.5–5.3% lower executor time; it does not replace '
         'the single-scan evidence.\n\n'
         'An independent K3 observer confirms dense switches to the direct callback '
         'after 64 consecutive misses. Eighteen untimed reports do not explain the '
         'remaining old K3 latency regression. No threshold or production policy was '
         'retuned. Complete packets retain all raw data, negative controls, absolute '
         'dispersions, source patches and reproduction instructions.\n\n'
         'The heap/caching direction has prior context, not an algorithmic novelty '
         'claim: https://www.postgresql.org/message-id/52F373CC.4050800%40vmware.com\n\n')
draft += '\n'.join(name + ': ' + link for name, link in links.items()) + '\n'
(OUT / 'email-draft-overview-UNSENT.txt').write_text(draft)
files = {}
for path in sorted(OUT.iterdir()):
    data = path.read_bytes()
    files[path.name] = dict(bytes=len(data), sha256=hashlib.sha256(data).hexdigest(),
                            md5=hashlib.md5(data).hexdigest())
manifest = dict(status='FROZEN_AFTER_ROOT_REVIEW', utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                files=files, complete_verified_packets=3, final_live_stopped_lifetimes=21,
                no_new_source_or_benchmark=True)
(OUT / 'MANIFEST.json').write_text(json.dumps(manifest, indent=2) + '\n')
print(json.dumps(dict(status=manifest['status'], files=len(files) + 1,
                      bytes=sum(p.stat().st_size for p in OUT.iterdir()))))
