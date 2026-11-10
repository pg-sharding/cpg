#!/usr/bin/env python3
"""Source replay/projection only: no compiler or PostgreSQL invocation."""
import argparse
import hashlib
import json
import pathlib
import subprocess
import tempfile

HERE = pathlib.Path(__file__).resolve().parent


def sha(p):
    return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--base-source', type=pathlib.Path,
                   default=HERE.parent / 'source-prototype-K3/source/src/backend/access/gin/ginlogic.c')
    p.add_argument('--out-new', type=pathlib.Path, required=True)
    a = p.parse_args()
    assert not a.out_new.exists()
    source = json.loads((HERE / 'SOURCE.json').read_text())
    assert sha(a.base_source) == source['original_ginlogic_sha256']
    target = HERE / 'source/src/backend/access/gin/ginlogic.c'
    text = target.read_text()
    remove = ['#include "lib/stringinfo.h"\n', '\n#include "ginlogic-probe.inc"\n',
              '\tk3diag_native(key, key->triConsistentFn == directTriConsistentFn);\n',
              '\n\tk3diag_cached_entry(key);\n',
              '\t\tk3diag_hit(key, cache->misses);\n',
              '\t\tk3diag_miss(key, cache->misses, true);\n',
              '\tk3diag_miss(key, cache->misses, false);\n',
              '\tk3diag_init(key, key->triConsistentFn == cachedTsqueryTriConsistentFn);\n']
    for inserted in remove:
        assert text.count(inserted) == 1, inserted
        text = text.replace(inserted, '')
    assert text == a.base_source.read_text()
    for name, v in source['files'].items():
        path = HERE / 'source' / name
        assert sha(path) == v['sha256'] and path.stat().st_size == v['bytes']
    assert (HERE / 'ginlogic-probe.inc').read_bytes() == (HERE / 'source/src/backend/access/gin/ginlogic-probe.inc').read_bytes()
    assert sha(HERE / 'diagnostic-over-exact-K3.diff') == source['diagnostic_diff_sha256']
    with tempfile.TemporaryDirectory(prefix='k3-diag-static-', dir='/private/tmp') as directory:
        root = pathlib.Path(directory)
        path = root / 'src/backend/access/gin/ginlogic.c'
        path.parent.mkdir(parents=True)
        path.write_bytes(a.base_source.read_bytes())
        subprocess.run(['git', 'init', '--quiet'], cwd=root, check=True)
        patch = (HERE / 'diagnostic-over-exact-K3.diff').resolve()
        subprocess.run(['git', 'apply', '--check', str(patch)], cwd=root, check=True)
        subprocess.run(['git', 'apply', str(patch)], cwd=root, check=True)
        for name in source['files']:
            assert (root / name).read_bytes() == (HERE / 'source' / name).read_bytes()
    cases = json.loads((HERE / 'CASES.json').read_text())
    assert len(cases['cases']) == cases['reports'] == 18
    assert sum(c['kind'] == 'sql' for c in cases['cases']) == 6
    assert sum(c['kind'] == 'am' for c in cases['cases']) == 12
    protocol_path = HERE.parent / 'timing-prep-r1/PROTOCOL.json'
    answers_path = HERE.parent / 'qualification/inputs/answers.json'
    assert sha(protocol_path) == source['case_source']['protocol_sha256']
    assert sha(answers_path) == source['case_source']['answers_sha256']
    protocol = json.loads(protocol_path.read_text())
    answers = json.loads(answers_path.read_text())
    original = {c['name']: c for c in protocol['cases']}
    for case in cases['cases']:
        name = case['name'].split('/', 1)[-1] if case['kind'] == 'sql' else case['name'].split('/')[0]
        parent = original[name]
        if case['kind'] == 'sql':
            assert all(case[key] == parent[key] for key in ['sql', 'rows_sql', 'settings'])
            assert case['answer'] == answers[name]
        else:
            assert case['query'] == parent['query'] and case['index'] == 'g1.' + parent['index']
            assert case['loops'] in [1, 3] and case['total_tids'] == case['loops'] * parent['tids_per_scan']
    result = dict(status='PASS_STATIC_PROJECTION_AND_STRICT_APPLY_ONLY',
                  original_ginlogic_sha256=sha(a.base_source), insertion_sites=6,
                  projection_recovers_parent_byte_exact=True, strict_patch_apply=True,
                  source_snapshot_hashes=True, exact_parent_SQL_answers_and_AM_inputs=True,
                  prospective_reports=18,
                  compiler_invocations=0, VM_actions=0, runtime='NOT_EXECUTED',
                  scope='C syntax/export/normal TU and runtime behavior await independent review and a separate approved build.')
    a.out_new.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result))


if __name__ == '__main__':
    main()
