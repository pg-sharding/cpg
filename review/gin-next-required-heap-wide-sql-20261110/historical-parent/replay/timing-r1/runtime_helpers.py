"""Actual public-API AM module compilation and ordinary valid-query answer checks."""
import gzip
import hashlib
import json
import pathlib
import shlex
import shutil
import subprocess
import time


def compile_micro(root, out, prefix, bc):
    source = root / 'gin-am-micro.c'
    pg = prefix / 'bin/pg_config'
    flags = shlex.split(bc.capture([pg, '--cflags'], prefix)) + shlex.split(bc.capture([pg, '--cppflags'], prefix))
    headers = pathlib.Path(bc.capture([pg, '--includedir-server'], prefix).strip())
    obj, module = out / 'gin-am-micro.o', out / 'gin-am-micro.so'
    bc.run(['gcc', *flags, '-Werror', '-fPIC', '-I' + str(headers),
            '-I' + str(prefix / 'include'), '-c', source, '-o', obj], out / 'micro-compile.log', prefix=prefix)
    bc.run(['gcc', '-shared', '-fno-lto', obj, '-o', module], out / 'micro-link.log', prefix=prefix)
    bc.save(out / 'module.json', dict(status='PASS_COMPILE', source_sha256=bc.sha(source),
            module_sha256=bc.sha(module), prefix=str(prefix),
            headers_sha256=hashlib.sha256(json.dumps(bc.inventory(headers), sort_keys=True).encode()).hexdigest(),
            scope='Real index_rescan/index_getbitmap/tbm_free loop; no modeled loader, private GIN structure or extracted scan body.'))
    return module


def qualify_micro(session, cases):
    result = {}
    for c in cases:
        query = c['sql'].rsplit(', ', 1)[0] + ', 2)'
        value = session.json(query)
        assert value['loops'] == 2 and value['total_tids'] == c['tids_per_scan'] * 2
        assert value['cpu_ns'] > 0 and value['wall_ns'] > 0
        result[c['name']] = value
    return result


