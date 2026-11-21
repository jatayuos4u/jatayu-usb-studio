#!/usr/bin/env python3
"""Beta 11 fail-closed, read-only live device revalidation.

This module never opens block devices and never authorizes writing.
The snapshot is only advisory; a future privileged writer must validate
against its own opened descriptor, mounts, topology and Polkit subject.
"""
from dataclasses import dataclass
import os
from pathlib import Path
import stat

class DeviceRejected(ValueError):
    pass

@dataclass(frozen=True)
class DeviceFingerprint:
    path: str
    major: int
    minor: int
    size_bytes: int
    sysfs_path: str
    serial: str


def inspect_device(path, *, dev_root=Path('/dev'), sys_root=Path('/sys')):
    if not isinstance(path, str) or not path.startswith('/dev/'):
        raise DeviceRejected('Invalid device path')
    name = path[5:]
    if not name or '/' in name or name in ('.', '..') or not name.isascii() or not all(c.isalnum() or c in '_-' for c in name):
        raise DeviceRejected('Only direct block-device names are accepted')
    dev = dev_root / name
    info = os.lstat(dev)
    if not stat.S_ISBLK(info.st_mode):
        raise DeviceRejected('Not a block device')
    sys_entry = sys_root / 'class' / 'block' / name
    sysdev = sys_entry.resolve(strict=True)
    if (sysdev / 'partition').exists():
        raise DeviceRejected('Partition is not a whole disk')
    if not any(part.name.startswith('usb') for part in (sysdev, *sysdev.parents)):
        raise DeviceRejected('USB ancestry not confirmed')
    try:
        major, minor = (int(v) for v in (sysdev / 'dev').read_text().strip().split(':'))
        sectors = int((sysdev / 'size').read_text().strip())
    except (OSError, ValueError) as exc:
        raise DeviceRejected('Missing kernel identity') from exc
    if (major, minor) != (os.major(info.st_rdev), os.minor(info.st_rdev)) or sectors <= 0:
        raise DeviceRejected('Kernel identity mismatch')
    serial_path = sysdev / 'device' / 'serial'
    serial = serial_path.read_text().strip() if serial_path.exists() else ''
    return DeviceFingerprint(path, major, minor, sectors * 512, str(sysdev), serial)


def compare_fingerprints(expected, actual):
    if not isinstance(expected, DeviceFingerprint) or not isinstance(actual, DeviceFingerprint):
        raise DeviceRejected('Invalid fingerprint')
    if expected != actual:
        raise DeviceRejected('Device identity changed; reselect USB drive')
    return True


def check_live(expected, *, inspector=inspect_device):
    """Non-authorizing inspection: return a structured fail-closed report."""
    try:
        actual = inspector(expected.path)
        compare_fingerprints(expected, actual)
    except (OSError, ValueError, TypeError, AttributeError) as exc:
        return {'ok': False, 'writing_authorized': False, 'reason': str(exc)}
    return {'ok': True, 'writing_authorized': False,
            'reason': 'Live identity matches; no writing authorization granted'}
