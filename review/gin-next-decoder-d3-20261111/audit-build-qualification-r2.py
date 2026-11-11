#!/usr/bin/env python3
"""Recount selected D3 build/ordinary valid-input proofs locally; no DB, compiler or network."""
import argparse
import hashlib
import importlib.util
import json
import pathlib
import shlex
import time

HERE = pathlib.Path(__file__).resolve().parent
ROLES = ['B', 'D2', 'D3', 'D3_assert']
SOURCE_SHA = '59e277145711e1a3ad4ed3e942f9120c94203417071b0c3d27eda75634209007'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path):
    return json.loads(path.read_text())


def nodes(node):
    yield node
    for child in node.get('Plans', []):
        yield from nodes(child)


def boundary_reference():
    """Integer TIDs and bit-length sizes, independent of module and gate generator."""
    cases = []
    for pattern in range(6):
        for n in [2, 3, 4, 5, 6, 9, 17, 128]:
            positions = [1]
            for delta_index in range(1, n):
                large = delta_index % 2 == 1 if pattern == 5 else delta_index == pattern + 1
                positions.append(positions[-1] + (2048 if large else 1))
            checksum = 1469598103934665603
            for packed in positions:
                block, offset = divmod(packed, 2048)
                assert 0 < offset < 2048
                for value in [block, offset]:
                    checksum = ((checksum ^ value) * 1099511628211) % (1 << 64)
            for segment in [4, 127]:
                for first in [0, 1]:
                    start = size = segments = 0
                    while start < n:
                        count = 1 if first and start == 0 else min(segment, n - start)
                        part = positions[start:start + count]
                        encoded = sum(max(1, ((b - a).bit_length() + 6) // 7)
                                      for a, b in zip(part, part[1:]))
                        size += 8 + encoded + encoded % 2
                        segments += 1
                        start += count
                    cases.append(dict(name=f'mixed-p{pattern}-n{n}-s{segment}-f{first}',
                                      items=n, bytes=size, segments=segments, checksum=str(checksum)))
    return dict(status='PASS_VALID_MIXED_BOUNDARIES', timing_samples=0, cases=cases,
                checked_cases=len(cases), decode_calls=2 * len(cases),
                checked_items=sum(2 * case['items'] for case in cases))


def expected_native():
    spec = importlib.util.spec_from_file_location('d3_independent_arithmetic',
                                                HERE / 'timing-prep-r1/audit-independent-r1.py')
    own = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(own)
    cases = []
    for name, n, shift, segment, first, loops in own.DECODE:
        value = own.decoder_expected(n, shift, segment, first, loops)
        cases.append(dict(name=name, items=n, bytes=value['compressed_bytes'],
                          segments=value['segments'], checksum=value['checksum']))
    return dict(status='PASS_VALID_DECODER', timing_samples=0, cases=cases,
                checked_items=sum(case['items'] for case in cases))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--evidence', type=pathlib.Path, required=True)
    parser.add_argument('--output', type=pathlib.Path, required=True)
    args = parser.parse_args()
    assert not args.output.exists()
    out = dict(status='RUNNING_LOCAL_METADATA_RECOUNT', started_ns=time.time_ns(), timing_samples=0)
    try:
        root = args.evidence
        build = root / 'build-r1'
        qualification = root / 'qualification-r1'
        collection = load(root / 'COLLECTION.json')
        assert collection['status'] == 'BOUNDED_D3_TEXT_COLLECTION'
        assert collection['stage'] in ['qualification', 'smoke', 'full']
        assert 300 < len(collection['files']) < 600
        for name, value in collection['files'].items():
            path = root / name
            assert not pathlib.PurePosixPath(name).is_absolute() and '..' not in pathlib.PurePosixPath(name).parts
            assert not path.is_symlink() and path.is_file()
            assert path.stat().st_size == value['bytes'] and sha(path) == value['sha256'], name

        receipt = load(build / 'build-receipt.json')
        build_status = load(build / 'status.json')
        gate = load(qualification / 'status.json')
        plan = load(HERE / 'build-source/SOURCE.json')
        baseline = {name: {key: value[key] for key in ['bytes', 'sha256']}
                    for name, value in load(HERE / 'build-source/base-source-files.json').items()}
        assert receipt['status'] == build_status['status'] == 'PASS_GIN_D3_MATCHED_BUILDS'
        assert build_status['core_cleanup_errors'] == [] and receipt['core239_each']
        assert set(receipt['variants']) == set(ROLES)
        assert receipt['source_plan_sha256'] == gate['source_plan_sha256'] == sha(HERE / 'build-source/SOURCE.json') == SOURCE_SHA
        assert gate['status'] == 'PASS_D3_ORDINARY_SQL_AND_VALID_DECODER'
        assert gate['remaining_owned'] == gate['timing_samples'] == 0 and gate['cleanup_errors'] == []
        assert gate['build_receipt_sha256'] == sha(build / 'build-receipt.json')
        assert (gate['decoder_cases_per_variant'], gate['mixed_boundary_cases_per_variant'],
                gate['mixed_boundary_item_checks_per_variant']) == (21, 192, 8352)
        for name in ['BUILD-INPUTS-D3-r1.json', 'QUALIFICATION-INPUTS-D3-r1.json', 'TIMING-INPUTS-D3-r1.json']:
            for member, value in load(HERE / name)['files'].items():
                path = HERE / member
                assert path.stat().st_size == value['bytes'] and sha(path) == value['sha256'], member
        for name, value in load(qualification / 'frozen-inputs.json').items():
            assert sha(HERE / 'qualification' / name) == value['sha256'], name

        reference = load(HERE / 'qualification/reference-B.json')
        cases = (load(HERE / 'qualification/inputs/queries.json')['cases'] +
                 load(HERE / 'qualification/inputs/queries-holdout.json')['cases'])
        answers = load(HERE / 'qualification/inputs/answers.json')
        assert len(cases) == 25 and len(reference['rows']) == 47
        native = expected_native()
        legacy = dict(native, cases=native['cases'][:18], checked_items=13152)
        assert sum(case['items'] for case in legacy['cases']) == 13152
        assert legacy == reference['decoder']
        assert len(native['cases']) == 21 and native['checked_items'] == 13536
        boundary = boundary_reference()
        mixed = load(HERE / 'qualification/mixed-reference.json')
        assert native['cases'][18:] == mixed['decoder_extra']
        assert boundary == mixed['boundaries']
        assert (boundary['checked_cases'], boundary['decode_calls'], boundary['checked_items']) == (192, 384, 8352)

        base_objects = load(build / 'B-backend-objects.json')
        base_headers = load(build / 'B-headers.json')
        roles = {}
        ordered = lifecycle = decoder_cases = decoder_items = boundary_cases = boundary_calls = boundary_items = 0
        for role in ROLES:
            label = 'D3' if role == 'D3_assert' else role
            variant = receipt['variants'][role]
            assert variant['commit'] == plan['variants'][label]['commit']
            assert variant['assertions'] == role.endswith('_assert')
            wanted = dict(baseline)
            wanted.update(plan['variants'][label]['source_files'])
            source_path = build / (role + '-source-inventory.json')
            source = load(source_path)
            assert len(source) == 7726 and source == wanted
            assert variant['source_manifest_sha256'] == sha(source_path)
            assert variant['source_edited_files'] == plan['variants'][label]['source_files']
            assert variant['expected_files_unchanged'] and variant['core239'] and variant['postinglist_check']
            for check in ['core239', 'postinglist-check']:
                assert load(build / (role + '-' + check + '.log.command.json'))['returncode'] == 0
            headers_path = build / (role + '-headers.json')
            headers = load(headers_path)
            assert len(headers) == 907 and headers == variant['headers']
            assert sha(headers_path) == variant['headers_sha256']
            objects_path = build / (role + '-backend-objects.json')
            objects = load(objects_path)
            assert sha(objects_path) == variant['backend_objects_sha256']
            changed = None
            if role != 'D3_assert':
                assert headers == base_headers and objects.keys() == base_objects.keys()
                changed = [name for name in objects if objects[name] != base_objects[name]]
                assert set(changed) <= {'access/gin/ginpostinglist.o'}
                assert changed == variant['changed_backend_objects_from_B']
                for unit, value in variant['normal_objects'].items():
                    assert sha(build / pathlib.Path(value['asm']).name) == value['asm_sha256']
                    assert objects['access/gin/' + unit + '.o']['sha256'] == value['object_sha256']
            else:
                # Assert builds have distinct flags and intentionally omit the release comparison.
                assert 'changed_backend_objects_from_B' not in variant
                assert variant['normal_objects'] == {}

            result_path = qualification / role / 'result.json'
            result = load(result_path)
            assert result['status'] == 'PASS' and result['timing_samples'] == 0
            assert sha(result_path) == gate['variants'][role]['sha256']
            assert result['source_commit'] == variant['commit']
            assert result['postgres_sha256'] == variant['postgres_sha256']
            assert result['headers_sha256'] == variant['headers_sha256']
            assert result['module_source_sha256'] == sha(HERE / 'qualification/decoder-native.c')
            assert result['production_flags'] == shlex.split(variant['cflags']) + shlex.split(variant['cppflags'])
            assert result['decoder'] == load(qualification / role / 'decoder-raw.txt') == native
            assert result['mixed_boundaries'] == load(qualification / role / 'boundary-raw.txt') == boundary
            decoder_cases += 21
            decoder_items += 13536
            boundary_cases += 192
            boundary_calls += 384
            boundary_items += 8352
            assert len(result['cases']) == 25 and len(result['extra_cases']) == 15 and len(result['prepared']) == 7
            for case in cases:
                name = case['name']
                value = result['cases'][name]
                proof = load(qualification / (role + '-' + name + '.json'))
                assert value['literal'] == answers[name]
                assert value['multiset'] == reference['rows'][name] == proof['actual'] == proof['reference']
                indexes = [node['Index Name'] for node in nodes(value['plan']) if 'Index Name' in node]
                assert case['index'] in indexes if case['index'] else not indexes
                ordered += 1
            for name, value in result['extra_cases'].items():
                assert value['actual'] == value['reference'] == reference['rows'][name]
                assert int(value['count']) == value['actual']['rows']
                ordered += 1
            for query, value in result['prepared'].items():
                assert value['actual'] == value['reference'] == value['repeated'] == reference['rows']['prepared-' + query]
                ordered += 1
            assert result['lifecycle'] == reference['lifecycle']
            for phase, values in result['lifecycle'].items():
                for query, value in values.items():
                    name = 'writes-' + phase + '-' + query.replace(' ', '').replace('&', 'and').replace('|', 'or')
                    proof = load(qualification / (role + '-' + name + '.json'))
                    assert proof['actual'] == proof['reference'] == value
                    lifecycle += 1
            roles[role] = dict(commit=variant['commit'], postgres_sha256=variant['postgres_sha256'],
                               headers=907, source_files=7726, changed_backend_objects_vs_B=changed,
                               backend_object_comparison_scope='not_applicable_assert_build' if role.endswith('_assert') else 'release_objects_compared_with_B',
                               decoder_cases=21, decoder_items=13536, boundary_cases=192,
                               boundary_decode_calls=384, boundary_item_checks=8352,
                               module_sha256=result['module_sha256'])
        assert (ordered, lifecycle, decoder_cases, decoder_items) == (188, 48, 84, 54144)
        assert (boundary_cases, boundary_calls, boundary_items) == (768, 1536, 33408)
        assert len(gate['clusters']) == 5
        for cluster in gate['clusters']:
            assert cluster['stopped']
            assert cluster['stop_proof'] == dict(pg_ctl_status_rc=3, cluster_state='shut down', pidfile_absent=True)
        out.update(status='PASS_INDEPENDENT_D3_BUILD_AND_ORDINARY_QUALIFICATION_RECOUNT',
                   selected_text_files=len(collection['files']),
                   selected_text_bytes=sum(value['bytes'] for value in collection['files'].values()),
                   roles=roles, core239_builds=4, postinglist_builds=4, source_expected_unchanged=True,
                   decoder_cases=decoder_cases, decoder_item_checks=decoder_items,
                   boundary_cases=boundary_cases, boundary_decode_calls=boundary_calls, boundary_item_checks=boundary_items,
                   ordered_SQL_prepared_hash_comparisons=ordered, lifecycle_comparisons=lifecycle,
                   stopped_runtime_clusters=5, build_receipt_sha256=sha(build / 'build-receipt.json'),
                   qualification_status_sha256=sha(qualification / 'status.json'), source_plan_sha256=SOURCE_SHA,
                   scope='Local recount of selected exact text proofs; no new live inspection or runtime execution.',
                   finished_ns=time.time_ns())
    except BaseException as exc:
        out.update(status='FAILED_PRESERVED', error=repr(exc))
        raise
    finally:
        args.output.write_text(json.dumps(out, indent=2) + '\n')
    print(json.dumps(out))


if __name__ == '__main__':
    main()
