#!/usr/bin/env python3
"""Non-privileged, read-only guard for future writer architecture.

This module never opens a block device. No authorization or write API exists.
"""
import os
import re
import stat
from pathlib import Path

DEVICE = re.compile(r"^/dev/[A-Za-z0-9._/-]+$")
SYSTEM_MOUNTS = {'/', '/home', '/boot', '/boot/efi', '/usr', '/var'}


def _walk(node, ancestors=()):
    path = node.get('path') or '/dev/' + node.get('name', '')
    chain = ancestors + (path,)
    yield node, chain
    for child in node.get('children') or []:
        yield from _walk(child, chain)


def guard(snapshot, target, iso, *, device_identity=None, expected_identity=None):
    """Return a non-authorizing report. Snapshot may be stale at any time."""
    reasons = []
    if not isinstance(target, str) or not DEVICE.fullmatch(target) or '..' in target:
        return {'candidate_checks_passed': False, 'allowed_to_write': False, 'read_only': True,
                'reasons': ['Invalid target path']}
    nodes = [item for root in snapshot.get('blockdevices', []) for item in _walk(root)]
    matches = [(n, chain) for n, chain in nodes if chain[-1] == target]
    if len(matches) != 1:
        reasons.append('Target must uniquely identify a device')
    else:
        node, chain = matches[0]
        if node.get('type') != 'disk' or str(node.get('tran') or '').lower() != 'usb':
            reasons.append('Target is not a USB whole disk')
        if not isinstance(node.get('size'), int) or node['size'] <= 0:
            reasons.append('Target capacity is unknown')
        descendants = [n for n, c in nodes if c[:len(chain)] == chain]
        if any(any(m for m in (n.get('mountpoints') or [])) for n in descendants):
            reasons.append('USB contains mounted partitions')
        if any(str(n.get('fstype') or '').lower() == 'swap' for n in descendants):
            reasons.append('USB contains swap')
        if any(any(m in SYSTEM_MOUNTS for m in (n.get('mountpoints') or []) if m) for n in descendants):
            reasons.append('USB contains system mount')
    if expected_identity is not None and device_identity != expected_identity:
        reasons.append('Device identity changed since selection')
    try:
        f = Path(iso)
        if f.suffix.lower() != '.iso' or not f.is_file():
            reasons.append('ISO is missing or has invalid extension')
        else:
            size = f.stat().st_size
            if size <= 0:
                reasons.append('ISO is empty')
            if len(matches) == 1 and isinstance(matches[0][0].get('size'), int) and size > matches[0][0]['size']:
                reasons.append('ISO exceeds device capacity')
    except (OSError, TypeError, ValueError):
        reasons.append('ISO cannot be inspected')
    return {'candidate_checks_passed': not reasons, 'allowed_to_write': False,
            'read_only': True, 'reasons': reasons,
            'warning': 'Snapshot inspection is not authorization. A future privileged writer must revalidate live state.'}
