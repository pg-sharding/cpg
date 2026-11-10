#!/usr/bin/env python3
"""Extract exact frozen production fragments; no compiler or execution."""
import argparse
import hashlib
import json
import pathlib

HERE = pathlib.Path(__file__).resolve().parent
SOURCE_SHA = '0c474bdfce5ce24a91c0706b66428f1b80870e8433d7fa30589e18580e48cbc2'


def fragments(source):
    assert hashlib.sha256(source).hexdigest() == SOURCE_SHA
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


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source', type=pathlib.Path,
                   default=HERE.parent / 'source/src/backend/access/gin/ginget.c')
    p.add_argument('--output-new', type=pathlib.Path, required=True)
    a = p.parse_args()
    data = fragments(a.source.read_bytes())
    data['offset-property.c'] = (HERE / 'offset-property.c').read_bytes()
    a.output_new.mkdir()
    for name, value in data.items():
        (a.output_new / name).write_bytes(value)
    receipt = dict(status='EXTRACTED_ONLY_NOT_COMPILED_OR_EXECUTED', source_sha256=SOURCE_SHA,
                   source=str(a.source.resolve()), files={n: dict(bytes=len(b), sha256=hashlib.sha256(b).hexdigest()) for n, b in data.items()})
    (a.output_new / 'EXTRACTION.json').write_text(json.dumps(receipt, indent=2) + '\n')
    print(json.dumps(receipt))


if __name__ == '__main__':
    main()
