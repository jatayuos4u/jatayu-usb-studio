#!/usr/bin/env python3
"""Beta 12 independent fail-closed read-only checks; never grants write access."""
import hashlib
import os
from pathlib import Path

class SafetyFailure(ValueError):
    pass

def _devnums(text):
    """Extract major:minor from Linux mountinfo, ignoring untrusted mount paths."""
    found = set()
    for line in text.splitlines():
        parts = line.split()
        if len(parts) < 6 or '-' not in parts:
            raise SafetyFailure('Malformed mountinfo')
        pair = parts[2].split(':')
        if len(pair) != 2:
            raise SafetyFailure('Malformed mount device number')
        try:
            found.add((int(pair[0]), int(pair[1])))
        except ValueError as exc:
            raise SafetyFailure('Malformed mount device number') from exc
    return found

def inspect_usage(fingerprint, *, sys_root=Path('/sys'), mountinfo=Path('/proc/self/mountinfo'), swaps=Path('/proc/swaps')):
    """Reject disk if any descendant partition is mounted or active swap.

    Snapshot only: not safe to use as authorization for a later write.
    """
    from device_revalidation import inspect_device, compare_fingerprints
    compare_fingerprints(fingerprint, inspect_device(fingerprint.path, sys_root=sys_root))
    parent = sys_root / 'class' / 'block' / Path(fingerprint.path).name
    try:
        mounted = _devnums(mountinfo.read_text())
        swap_lines = swaps.read_text().splitlines()[1:]
        swap_paths = {line.split()[0] for line in swap_lines if line.split()}
        nodes = [parent] + [p for p in parent.iterdir() if (p / 'partition').exists()]
        for node in nodes:
            maj, minor = map(int, (node / 'dev').read_text().strip().split(':'))
            if (maj, minor) in mounted:
                raise SafetyFailure('Selected disk or partition is mounted')
            if '/dev/' + node.name in swap_paths:
                raise SafetyFailure('Selected disk or partition is swap')
            if (node / 'holders').exists() and any((node / 'holders').iterdir()):
                raise SafetyFailure('Device has active kernel holders')
    except (OSError, ValueError) as exc:
        raise SafetyFailure('Cannot establish safe device usage: ' + str(exc)) from exc
    return {'safe_snapshot': True, 'writing_authorized': False,
            'warning': 'Snapshot only; privileged service must revalidate atomically'}

def inspect_iso(path, *, expected_sha256=None, chunk_size=1024*1024):
    """Read-only ISO integrity check; checksum is only trusted if supplied independently."""
    if not isinstance(path, str) or not os.path.isabs(path) or not os.path.isfile(path):
        raise SafetyFailure('ISO must be a regular absolute file')
    if os.path.islink(path):
        raise SafetyFailure('ISO symlink rejected')
    digest = hashlib.sha256()
    with open(path, 'rb') as stream:
        before = os.fstat(stream.fileno())
        if before.st_size <= 0:
            raise SafetyFailure('ISO is empty')
        while True:
            data = stream.read(chunk_size)
            if not data: break
            digest.update(data)
        after = os.fstat(stream.fileno())
    if (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns) != (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns):
        raise SafetyFailure('ISO changed during hashing')
    result = digest.hexdigest()
    if expected_sha256 is not None:
        if not isinstance(expected_sha256, str) or len(expected_sha256) != 64 or any(c not in '0123456789abcdefABCDEF' for c in expected_sha256):
            raise SafetyFailure('Invalid expected SHA-256')
        if result.lower() != expected_sha256.lower():
            raise SafetyFailure('ISO checksum mismatch')
    return {'size_bytes': before.st_size, 'sha256': result,
            'checksum_verified': expected_sha256 is not None, 'writing_authorized': False}
