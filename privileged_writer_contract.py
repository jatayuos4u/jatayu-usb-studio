#!/usr/bin/env python3
"""Beta 8 privileged writer boundary CONTRACT ONLY. No write implementation."""
from dataclasses import dataclass
from pathlib import Path
import json
import os
import stat
import subprocess

@dataclass(frozen=True)
class DeviceIdentity:
    path: str
    major: int
    minor: int
    sysfs_path: str
    size_bytes: int
    transport: str
    serial: str

def inspect_live(path, *, sys_root=Path('/sys'), dev_root=Path('/dev')):
    """Read current kernel identity. Reject aliases, partitions and unsafe paths."""
    if not isinstance(path, str) or not path.startswith('/dev/') or '/' in path[5:]:
        raise ValueError('Target must be a direct /dev disk path')
    name = path[5:]
    if not name or name in ('.', '..'):
        raise ValueError('Invalid device name')
    device = dev_root / name
    info = os.lstat(device)
    if not stat.S_ISBLK(info.st_mode):
        raise ValueError('Target is not a block device')
    if not (sys_root / 'class/block' / name).exists():
        raise ValueError('Device is not in sysfs')
    sysdev = (sys_root / 'class/block' / name).resolve(strict=True)
    if (sysdev / 'partition').exists():
        raise ValueError('Partitions are not allowed')
    size = int((sysdev / 'size').read_text().strip()) * 512
    if size <= 0:
        raise ValueError('Invalid capacity')
    # USB transport must be supported by the kernel device ancestry.
    if not any(p.name.startswith('usb') for p in (sysdev, *sysdev.parents)):
        raise ValueError('Device does not have a USB sysfs ancestor')
    serial_file = sysdev / 'device/serial'
    serial = serial_file.read_text().strip() if serial_file.exists() else ''
    return DeviceIdentity(path, os.major(info.st_rdev), os.minor(info.st_rdev),
                          str(sysdev), size, 'usb', serial)

def revalidate(expected, *, inspector=inspect_live):
    """Fail closed if a device is unplugged, replaced or its identity changes."""
    try:
        current = inspector(expected.path)
        return current == expected and current.size_bytes > 0
    except (OSError, ValueError, TypeError):
        return False

class DisabledPrivilegedWriter:
    """Proposed privileged service interface, intentionally not installed or activated."""
    def capabilities(self):
        return {'protocol_version': 1, 'privileged_writer_installed': False,
                'writing_enabled': False, 'polkit_enabled': False}
    def prepare(self, request):
        return {'authorized': False, 'status': 'blocked',
                'reason': 'Beta 8 has no privileged writer or write authorization'}
    def write(self, request):
        return self.prepare(request)

def main():
    print(json.dumps(DisabledPrivilegedWriter().capabilities(), indent=2))

if __name__ == '__main__':
    main()
