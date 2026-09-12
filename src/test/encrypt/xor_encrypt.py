#!/usr/bin/env python3
"""
PoC XOR encryption module for PostgreSQL pg_basebackup.

Usage in postgresql.conf:
  encrypt_command = 'python3 /path/to/xor_encrypt.py encrypt %f %p'
  decrypt_command = 'python3 /path/to/xor_encrypt.py decrypt %f %p'

Password is read from the XOR_ENCRYPT_PASSWORD environment variable.
Encrypts/decrypts the file in place (overwrites %p).
"""

import os
import sys
import tempfile

CHUNK_SIZE = 65536


def xor_bytes(data: bytes, key: bytes) -> bytes:
    return bytes(b ^ key[i % len(key)] for i, b in enumerate(data))


def get_password() -> bytes:
    pw = os.environ.get("XOR_ENCRYPT_PASSWORD")
    if not pw:
        sys.stderr.write("XOR_ENCRYPT_PASSWORD environment variable not set\n")
        sys.exit(1)
    return pw.encode("utf-8")


def encrypt(filepath: str) -> None:
    key = get_password()
    with open(filepath, "rb") as f:
        data = f.read()
    encrypted = xor_bytes(data, key)
    # Write to temp file then rename for atomicity
    fd, tmp = tempfile.mkstemp(dir=os.path.dirname(filepath), prefix=".xor_")
    try:
        os.write(fd, encrypted)
        os.fsync(fd)
        os.close(fd)
        os.rename(tmp, filepath)
    except Exception:
        os.close(fd) if not _fd_closed(fd) else None
        os.unlink(tmp)
        raise


def decrypt(filepath: str) -> None:
    # XOR is symmetric: decrypt == encrypt
    encrypt(filepath)


def _fd_closed(fd: int) -> bool:
    try:
        os.fstat(fd)
        return False
    except OSError:
        return True


def main() -> None:
    if len(sys.argv) != 4:
        sys.stderr.write(f"Usage: {sys.argv[0]} <encrypt|decrypt> <file> <path>\n")
        sys.exit(1)

    action = sys.argv[1]
    filepath = sys.argv[3]  # %p = full path

    if action == "encrypt":
        encrypt(filepath)
    elif action == "decrypt":
        decrypt(filepath)
    else:
        sys.stderr.write(f"Unknown action: {action}\n")
        sys.exit(1)


if __name__ == "__main__":
    main()
