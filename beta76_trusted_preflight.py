#!/usr/bin/env python3
"""Beta76: non-writing preflight. Caller-supplied identity is NEVER authoritative.

The caller of verify() must provide credentials obtained independently from the
system bus and a fresh inventory collected by a trusted service. No authorization
is granted by this module. It does not open devices for writing.
"""
from dataclasses import dataclass
import hashlib
import os
import re
import stat
from beta64_authorization import Denied
from beta75_writer_authorization import VerifiedContext

_HEX = re.compile(r"^[0-9a-f]{64}$")
_DEV = re.compile(r"^/dev/[a-zA-Z0-9._-]+$")

@dataclass(frozen=True)
class BusCredentials:
    sender: str
    uid: int
    pid: int

@dataclass(frozen=True)
class DeviceSnapshot:
    path: str
    major_minor: str
    sysfs: str
    size: int
    removable: bool
    read_only: bool
    mounted: bool
    system_disk: bool
    whole_disk: bool

class TrustedPreflight:
    """Requires independently collected bus credentials and device inventory.

    Snapshots are short-lived evidence, not authorization or a write capability.
    Production must recollect and compare immediately before any device open.
    """
    def verify(self, *, observed_sender, credentials, device, iso_path,
               expected_iso_sha256, expected_iso_size, expected_device=None):
        if not isinstance(credentials, BusCredentials) or not isinstance(device, DeviceSnapshot):
            raise Denied('Trusted credentials and device snapshot required')
        if not isinstance(observed_sender, str) or not observed_sender.startswith(':'):
            raise Denied('Missing authenticated sender')
        if credentials.sender != observed_sender or type(credentials.uid) is not int or credentials.uid < 0 or type(credentials.pid) is not int or credentials.pid <= 0:
            raise Denied('Untrusted bus credentials')
        if credentials.uid == 0:
            raise Denied('Root caller not supported')
        if not isinstance(device.path, str) or not _DEV.fullmatch(device.path):
            raise Denied('Invalid device path')
        if not isinstance(device.sysfs, str) or not device.sysfs.startswith('/sys/devices/'):
            raise Denied('Invalid sysfs identity')
        if not isinstance(device.major_minor, str) or not re.fullmatch(r'[0-9]+:[0-9]+', device.major_minor):
            raise Denied('Invalid major/minor')
        if type(device.size) is not int or device.size <= 0:
            raise Denied('Invalid capacity')
        if (device.removable is not True or device.read_only is not False or
            device.mounted is not False or device.system_disk is not False or
            device.whole_disk is not True):
            raise Denied('USB device is unsafe or cannot be verified')
        if expected_device is not None and device != expected_device:
            raise Denied('Device identity changed')
        if not isinstance(iso_path, str) or not os.path.isabs(iso_path):
            raise Denied('ISO path must be absolute')
        if not isinstance(expected_iso_sha256, str) or not _HEX.fullmatch(expected_iso_sha256):
            raise Denied('Invalid expected ISO digest')
        if type(expected_iso_size) is not int or expected_iso_size <= 0 or expected_iso_size > 128 * 1024**3:
            raise Denied('Invalid expected ISO size')
        # O_NOFOLLOW prevents final-component symlink traversal; fstat verifies
        # regular file. This is an inspection only, not a secure persistent handle.
        flags = os.O_RDONLY | getattr(os, 'O_NOFOLLOW', 0) | getattr(os, 'O_CLOEXEC', 0)
        try:
            fd = os.open(iso_path, flags)
        except OSError as exc:
            raise Denied('Cannot securely open ISO') from exc
        try:
            before = os.fstat(fd)
            if not stat.S_ISREG(before.st_mode) or before.st_size != expected_iso_size:
                raise Denied('ISO type or size mismatch')
            digest = hashlib.sha256()
            with os.fdopen(os.dup(fd), 'rb', closefd=True) as stream:
                while True:
                    chunk = stream.read(1024 * 1024)
                    if not chunk:
                        break
                    digest.update(chunk)
            after = os.fstat(fd)
            if (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns, before.st_ctime_ns) != (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns, after.st_ctime_ns):
                raise Denied('ISO changed during verification')
            if digest.hexdigest() != expected_iso_sha256:
                raise Denied('ISO checksum mismatch')
        finally:
            os.close(fd)
        context = VerifiedContext(credentials.sender, credentials.uid, device.major_minor,
                                  device.sysfs, expected_iso_sha256, expected_iso_size)
        context.as_intent()
        return context

    def request_write(self, *args, **kwargs):
        raise Denied('Physical USB writing disabled')
