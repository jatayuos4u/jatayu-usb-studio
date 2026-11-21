#!/usr/bin/env python3
"""Combined Beta 47/48 ISO preflight: read-only; NO block-device writes."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import stat

MAX_CHUNK = 1024 * 1024


def inspect_iso(path, expected_sha256=None):
    """Inspect a regular ISO file without following symlinks or touching a USB."""
    result = {'ok': False, 'authorized': False, 'writing_enabled': False,
              'read_only': True, 'stage': 'iso_preflight'}
    fd = None
    try:
        if not isinstance(path, str) or not path or path.startswith('/dev/'):
            raise ValueError('Choose a regular ISO file, not a device')
        fd = os.open(path, os.O_RDONLY | getattr(os, 'O_NOFOLLOW', 0) | getattr(os, 'O_CLOEXEC', 0) | getattr(os, 'O_NONBLOCK', 0))
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode) or info.st_size == 0:
            raise ValueError('ISO source must be a nonempty regular file')
        if not path.lower().endswith('.iso'):
            raise ValueError('Source must have an .iso extension')
        if expected_sha256 is not None and (len(expected_sha256) != 64 or any(c not in '0123456789abcdefABCDEF' for c in expected_sha256)):
            raise ValueError('Expected SHA-256 must contain 64 hexadecimal characters')
        h = hashlib.sha256()
        while True:
            chunk = os.read(fd, MAX_CHUNK)
            if not chunk: break
            h.update(chunk)
        after = os.fstat(fd)
        if (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns) != (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns):
            raise ValueError('ISO file changed during inspection')
        digest = h.hexdigest()
        if expected_sha256 is not None and digest != expected_sha256.lower():
            raise ValueError('ISO SHA-256 does not match supplied checksum')
        result.update(ok=True, iso_size_bytes=info.st_size, sha256=digest,
                      reason='ISO file preflight passed; physical USB writing is NOT authorized')
    except (OSError, ValueError) as exc:
        result['reason'] = str(exc)
    finally:
        if fd is not None: os.close(fd)
    return result


def main():
    parser = argparse.ArgumentParser(description='Read-only ISO preparation; never writes to USB')
    parser.add_argument('--iso', required=True)
    parser.add_argument('--sha256', help='Optional expected SHA-256')
    args = parser.parse_args()
    report = inspect_iso(args.iso, args.sha256)
    print(json.dumps(report, sort_keys=True))
    return 0 if report['ok'] else 1

if __name__ == '__main__':
    raise SystemExit(main())
