#!/usr/bin/env python3
"""Extract exact heap functions for a bounded valid-stream fragment oracle."""
import argparse
import hashlib
import json
import pathlib

HERE = pathlib.Path(__file__).resolve().parent
SOURCE_SHA = '91f3c7bbc1c22bb8400c114e31c3c34f572b21cf8289f3f72280e671d9d96c73'


def function(text, name, return_type):
    begin = text.index('static ' + return_type + '\n' + name + '(')
    opening = text.index('{', begin)
    depth = 1
    end = opening + 1
    while depth:
        depth += (text[end] == '{') - (text[end] == '}')
        end += 1
    return (text[begin:end] + '\n').encode()


def fragments(source):
    assert hashlib.sha256(source).hexdigest() == SOURCE_SHA
    text = source.decode()
    return {'heap-sift.inc': function(text, 'ginRequiredHeapSiftDown', 'void'),
            'heap-select.inc': function(text, 'ginRequiredHeapGetItem', 'bool')}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source', type=pathlib.Path, default=HERE.parent / 'source/src/backend/access/gin/ginget.c')
    p.add_argument('--output-new', type=pathlib.Path, required=True)
    a = p.parse_args()
    data = fragments(a.source.read_bytes())
    data['stream-property.c'] = (HERE / 'stream-property.c').read_bytes()
    a.output_new.mkdir()
    for name, value in data.items():
        (a.output_new / name).write_bytes(value)
    result = dict(status='EXTRACTED_ONLY_NOT_COMPILED_OR_EXECUTED', source_sha256=SOURCE_SHA,
                  files={n: dict(bytes=len(b), sha256=hashlib.sha256(b).hexdigest()) for n, b in data.items()})
    (a.output_new / 'EXTRACTION.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result))


if __name__ == '__main__':
    main()
