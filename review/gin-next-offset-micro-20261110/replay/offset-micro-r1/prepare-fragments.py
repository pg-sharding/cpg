#!/usr/bin/env python3
"""Extract frozen B/candidate offset fragments; no compilation or execution."""
import argparse
import hashlib
import json
import pathlib

HERE = pathlib.Path(__file__).resolve().parent
CANDIDATE_SHA = '0c474bdfce5ce24a91c0706b66428f1b80870e8433d7fa30589e18580e48cbc2'


def candidate_fragments(source):
    assert hashlib.sha256(source).hexdigest() == CANDIDATE_SHA
    text = source.decode()
    start = text.index('static inline int\nginAdvanceMatchOffsets(')
    end = text.index('\n#define gin_rand()', start)
    helper = text[start:end].rstrip() + '\n'
    start = text.index('\t\t\t\t/* Keep zero- and one-offset advances on the short path. */')
    end = text.index('\n\t\t\t}\n\n\t\t\tItemPointerSet', start)
    caller = text[start:end] + '\n'
    assert helper.count('ginAdvanceMatchOffsets(') == 1
    assert caller.count('ginAdvanceMatchOffsets(') == 1
    return {'match-helper.inc': helper.encode(), 'match-caller.inc': caller.encode()}


def extract(baseline, candidate):
    assert hashlib.sha256(baseline).hexdigest() == 'ca07396284189adf2180ab24dfd7549481a134348d4944ee6fb6c8f7d289e518'
    fragments = candidate_fragments(candidate)
    text = baseline.decode()
    begin = text.index('\t\t\t\t/* Otherwise scan to find the first item > advancePast */')
    end = text.index('\n\t\t\t}\n\n\t\t\tItemPointerSet', begin)
    fragments['baseline-caller.inc'] = (text[begin:end] + '\n').encode()
    return fragments


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--baseline', type=pathlib.Path,
                        default=HERE / 'inputs/ginget-B.c')
    parser.add_argument('--candidate', type=pathlib.Path,
                        default=HERE / 'inputs/ginget-Bitmap.c')
    parser.add_argument('--output-new', type=pathlib.Path, required=True)
    args = parser.parse_args()
    fragments = extract(args.baseline.read_bytes(), args.candidate.read_bytes())
    args.output_new.mkdir()
    for name, value in fragments.items():
        (args.output_new / name).write_bytes(value)
    status = dict(status='EXTRACTED_ONLY_NOT_COMPILED_OR_MEASURED',
                  files={n: dict(bytes=len(b), sha256=hashlib.sha256(b).hexdigest()) for n, b in fragments.items()})
    (args.output_new / 'EXTRACTION.json').write_text(json.dumps(status, indent=2) + '\n')
    print(json.dumps(status))


if __name__ == '__main__':
    main()
