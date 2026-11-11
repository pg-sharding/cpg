"""Independent integer TID/varbyte-size reference for the three declared mixed patterns and valid boundary cases."""
import argparse
import json
import pathlib


def record(name, n, pattern, segment_items, first_singleton):
    points = []
    packed = 1
    for item in range(n):
        if item:
            if pattern == -2:
                long_delta = item == 1
            elif pattern == -3:
                long_delta = item > 4
            elif pattern == -4:
                long_delta = item % 2 == 1
            else:
                assert -14 <= pattern <= -10
                long_delta = item == -pattern - 9
            packed += 2048 if long_delta else 1
        points.append(divmod(packed, 2048))
    assert all(0 < offset < 2048 for block, offset in points)
    checksum = 1469598103934665603
    for block, offset in points:
        for value in (block, offset):
            checksum = ((checksum ^ value) * 1099511628211) & ((1 << 64) - 1)
    position = length = segments = 0
    while position < n:
        count = 1 if first_singleton and position == 0 else min(segment_items, n - position)
        values = [block * 2048 + offset for block, offset in points[position:position + count]]
        encoded = 0
        for previous, current in zip(values, values[1:]):
            delta = current - previous
            encoded += 1
            while delta >= 128:
                delta //= 128
                encoded += 1
        length += 8 + encoded + encoded % 2
        segments += 1
        position += count
    return dict(name=name, items=n, bytes=length, segments=segments, checksum=str(checksum))


def reference():
    extra = [record(name, 128, pattern, 128, False) for name, pattern in [
        ('long_first_then_dense', -2), ('dense_first_then_long', -3), ('alternating_one_multibyte', -4)]]
    cases = []
    for pattern in range(6):
        for n in [2, 3, 4, 5, 6, 9, 17, 128]:
            for segment in [4, 127]:
                for first in [0, 1]:
                    cases.append(record(f'mixed-p{pattern}-n{n}-s{segment}-f{first}', n,
                                        -4 if pattern == 5 else -10 - pattern, segment, bool(first)))
    boundaries = dict(status='PASS_VALID_MIXED_BOUNDARIES', timing_samples=0, cases=cases,
                      checked_cases=len(cases), decode_calls=2 * len(cases),
                      checked_items=sum(2 * c['items'] for c in cases))
    assert len(cases) == 192 and boundaries['checked_items'] == 8352
    return dict(status='INDEPENDENT_VALID_TID_INTEGER_REFERENCE_NOT_CANDIDATE_SNAPSHOT',
                decoder_extra=extra, boundaries=boundaries,
                patterns={'long_first_then_dense': 'first delta2048; remaining126 deltas1',
                          'dense_first_then_long': 'first4 deltas1; remaining123 deltas2048',
                          'alternating_one_multibyte': 'odd delta index2048, even1;127 deltas'},
                timing_items=128, timing_loops=20000)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--compare', type=pathlib.Path, required=True)
    args = parser.parse_args()
    assert reference() == json.loads(args.compare.read_text())
    print(json.dumps(dict(status='PASS_INDEPENDENT_STATIC_MIXED_REFERENCE_RECONSTRUCTION',
                          timed_patterns=3, boundary_cases=192, boundary_item_checks=8352,
                          compiler_or_backend_execution='NOT_RUN')))
