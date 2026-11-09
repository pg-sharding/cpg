"""Finite psql conversation; timeout/exception cleanup affects only this client."""
import os
import queue
import signal
import subprocess
import threading


class Session:
    def __init__(self, psql, dsn, timeout=210, env=None):
        self.timeout = timeout
        self.serial = 0
        self.closed = False
        self.lines = queue.Queue()
        self.proc = subprocess.Popen(
            [str(psql), '-XAtq', '-v', 'ON_ERROR_STOP=1', '-d', dsn],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True,
            bufsize=1, start_new_session=True, env=env)
        self.reader = threading.Thread(target=self._read, daemon=True)
        self.reader.start()

    def _read(self):
        try:
            for line in self.proc.stdout:
                self.lines.put(line)
        finally:
            self.lines.put(None)

    def sql(self, text):
        assert not self.closed and text.rstrip().endswith(';')
        self.serial += 1
        token = '__HASH_ADDITIVE5_%d__' % self.serial
        self.proc.stdin.write(text + '\n\\echo ' + token + '\n')
        self.proc.stdin.flush()
        out = []
        # A finite statement_timeout also applies inside the server. The client
        # limit catches a stalled connection or process, outside SQL execution.
        import time
        deadline = time.monotonic() + self.timeout
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise TimeoutError('psql conversation deadline exceeded')
            try:
                line = self.lines.get(timeout=remaining)
            except queue.Empty as exc:
                raise TimeoutError('psql output deadline exceeded') from exc
            if line is None:
                raise RuntimeError(('psql EOF', self.proc.poll()))
            if line.rstrip('\n') == token:
                return ''.join(out).strip()
            out.append(line)
            if sum(map(len, out)) > 32 * 1024 * 1024:
                raise RuntimeError('unexpected psql result size')

    def close(self, failed=False):
        if self.closed:
            return
        self.closed = True
        try:
            self.proc.stdin.close()
        except (BrokenPipeError, OSError):
            pass
        try:
            self.proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            
            try:os.killpg(self.proc.pid, signal.SIGTERM)
            except ProcessLookupError:pass
            try:
                self.proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                
                try:os.killpg(self.proc.pid, signal.SIGKILL)
                except ProcessLookupError:pass
                self.proc.wait(timeout=5)
        self.reader.join(timeout=5)
        self.proc.stdout.close()
        if not failed:
            assert self.proc.returncode == 0, self.proc.returncode
