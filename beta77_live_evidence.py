#!/usr/bin/env python3
"""Beta77: read-only kernel-backed evidence. NEVER authorizes physical writing.

The sysfs and procfs roots are injectable for isolated tests. Production callers
must use kernel-mounted /sys and /proc, not user-provided paths. This is only a
snapshot; it is not a stable handle or a race-free authorization decision.
"""
import asyncio
import os
import re
from pathlib import Path
from beta64_authorization import Denied
from beta76_trusted_preflight import BusCredentials, DeviceSnapshot
from sender_identity import resolve_sender, validate_unique_name

_NAME = re.compile(r'^[a-zA-Z0-9._-]+$')

def _read(path):
    return path.read_text(encoding='ascii').strip()

def _devnums(text):
    try:
        major, minor = text.split(':')
        return int(major), int(minor)
    except (ValueError, AttributeError):
        raise Denied('Invalid kernel device number')

def _mount_devices(mountinfo):
    numbers = set()
    for line in mountinfo.splitlines():
        fields = line.split()
        if len(fields) < 10 or fields[2].count(':') != 1:
            raise Denied('Cannot safely parse mount information')
        numbers.add(_devnums(fields[2]))
    return numbers

def _swap_names(swaps):
    rows = swaps.splitlines()
    if not rows or not rows[0].startswith('Filename'):
        raise Denied('Cannot safely parse swap information')
    return [line.split()[0] for line in rows[1:] if line.split()]

def snapshot_device(path, *, sys_root='/sys', proc_root='/proc', dev_root='/dev'):
    """Read whole-disk facts, conservatively rejecting unknown dependencies.

    No device file is opened, no ioctl is performed, and no write is attempted.
    """
    if not isinstance(path, str) or not path.startswith('/dev/'):
        raise Denied('Invalid device path')
    name = path[5:]
    if not _NAME.fullmatch(name) or '/' in name:
        raise Denied('Invalid device name')
    sys_block = Path(sys_root) / 'class/block'
    node = sys_block / name
    try:
        resolved = node.resolve(strict=True)
        # No partitions, only whole disks.
        if (node / 'partition').exists():
            raise Denied('Partition is not a whole disk')
        devno = _read(node / 'dev')
        major, minor = _devnums(devno)
        size = int(_read(node / 'size')) * 512
        removable = _read(node / 'removable') == '1'
        read_only = _read(node / 'ro') != '0'
        if size <= 0:
            raise Denied('Invalid device capacity')
        mountinfo = _read(Path(proc_root) / 'self/mountinfo')
        mounted = (major, minor) in _mount_devices(mountinfo)
        # Conservatively block devices whose child partitions are mounted.
        for child in resolved.iterdir():
            if child.is_dir() and (child / 'partition').exists():
                mounted = mounted or _devnums(_read(child / 'dev')) in _mount_devices(mountinfo)
        swap_paths = _swap_names(_read(Path(proc_root) / 'swaps'))
        swap_in_use = any(s == path or s.startswith(path) for s in swap_paths)
        # Unknown topology is not safe: any active partition/mount/swap rejects.
        system_disk = mounted or swap_in_use
        sysfs = str(resolved)
        # Real sysfs must reside under /sys/devices; test roots can be temporary.
        if sys_root == '/sys' and not sysfs.startswith('/sys/devices/'):
            raise Denied('Unexpected sysfs location')
        # Do not trust the block device path alone to establish its identity.
        return DeviceSnapshot(path, devno, sysfs, size, removable, read_only,
                              mounted, system_disk, True)
    except Denied:
        raise
    except (OSError, ValueError, UnicodeError) as exc:
        raise Denied('Kernel inventory unavailable or inconsistent') from exc

async def credentials_from_transport(bus, message, *, timeout=3):
    """Read sender from actual transport envelope, never from request JSON."""
    sender = getattr(message, 'sender', None)
    if not validate_unique_name(sender):
        raise Denied('Missing authenticated D-Bus sender')
    try:
        identity = await asyncio.wait_for(resolve_sender(bus, sender), timeout=timeout)
    except Exception as exc:
        raise Denied('System bus credential lookup failed') from exc
    if (identity.unique_name != sender or type(identity.uid) is not int or
        type(identity.pid) is not int or identity.uid < 0 or identity.pid <= 0):
        raise Denied('System bus identity mismatch')
    return BusCredentials(sender, identity.uid, identity.pid)

def request_write(*args, **kwargs):
    raise Denied('Physical USB writing remains disabled')
