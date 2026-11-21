#!/usr/bin/env python3
"""Beta78 conservative, read-only storage dependency assessment.

Does not authorize USB writes. Kernel snapshots are not atomic. The production
service must validate opened descriptors, protected ancestors and live state.
"""
from pathlib import Path
from beta64_authorization import Denied
from beta77_live_evidence import snapshot_device, _mount_devices, _devnums, _read, _swap_names
import re

NAME = re.compile(r"^[A-Za-z0-9._-]+$")

def inspect_topology(device, *, sys_root='/sys', proc_root='/proc'):
    base = snapshot_device(device, sys_root=sys_root, proc_root=proc_root)
    name = device.removeprefix('/dev/')
    block = Path(sys_root) / 'class/block'
    mount_numbers = _mount_devices(_read(Path(proc_root)/'self/mountinfo'))
    swaps = _swap_names(_read(Path(proc_root)/'swaps'))
    visited = set()
    dependencies = []
    def visit(node_name):
        if not NAME.fullmatch(node_name):
            raise Denied('Invalid dependency name')
        if node_name in visited:
            raise Denied('Storage dependency cycle or duplicate')
        visited.add(node_name)
        if len(visited) > 128:
            raise Denied('Storage dependency graph too large')
        node = block/node_name
        if not node.exists():
            raise Denied(f'Missing sysfs block node for {node_name}')
        number = _devnums(_read(node/'dev'))
        if number in mount_numbers:
            raise Denied(f'Mounted storage dependency: {node_name}')
        if any(s == '/dev/'+node_name or s.startswith('/dev/'+node_name+'p') for s in swaps):
            raise Denied(f'Active swap dependency: {node_name}')
        dependencies.append(node_name)
        # Ordinary partition sysfs nodes may omit the optional 'slaves'
        # directory. Never infer that a stacked whole-disk node is safe.
        is_partition = (node / 'partition').exists()
        for direction in ('holders', 'slaves'):
            folder = node/direction
            if not folder.is_dir():
                if direction == 'slaves' and is_partition and not folder.exists():
                    continue
                raise Denied(f'Missing {direction} directory for {node_name} (sysfs topology incomplete)')
            try:
                children = sorted(folder.iterdir())
            except OSError as exc:
                raise Denied(f'Unreadable {direction} directory for {node_name}') from exc
            for child in children:
                if child.is_symlink() or child.is_dir():
                    visit(child.name)
                else:
                    raise Denied(f'Invalid storage dependency entry under {node_name}/{direction}')
        # Partition children must be considered too.
        for child in sorted(node.resolve().iterdir()):
            if child.is_dir() and (child/'partition').exists():
                visit(child.name)
    visit(name)
    # A clean topology remains only advisory; never a write permit.
    return {'device': device, 'dependencies': tuple(dependencies),
            'removable': base.removable, 'read_only': base.read_only,
            'mounted': base.mounted, 'system_disk': base.system_disk,
            'writing_enabled': False}

def request_write(*args, **kwargs):
    raise Denied('Physical USB writing remains disabled')
