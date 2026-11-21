#!/usr/bin/env python3
"""Read-only device risk assessment. Never opens block devices for writing."""
import argparse
import json
import os
import re
import subprocess

DEVICE = re.compile(r'^/dev/[a-zA-Z0-9._/-]+$')


def assess(snapshot, target):
    reasons = []
    if not DEVICE.fullmatch(target) or '..' in target:
        return {'allowed_to_write': False, 'read_only': True, 'candidate_checks_passed': False, 'reasons': ['Invalid device path']}
    disks = snapshot.get('blockdevices', [])
    roots = []
    def walk(node, ancestors=()):
        path = node.get('path') or ('/dev/' + node.get('name', ''))
        chain = ancestors + (path,)
        roots.append((node, chain))
        for child in node.get('children') or []:
            walk(child, chain)
    for disk in disks:
        walk(disk)
    matches = [(n, c) for n, c in roots if c[-1] == target]
    if len(matches) != 1:
        reasons.append('Target not uniquely present in block device snapshot')
    else:
        node, chain = matches[0]
        if node.get('type') != 'disk':
            reasons.append('Target is not a whole disk')
        if str(node.get('tran') or '').lower() != 'usb':
            reasons.append('Target transport is not USB')
        if not node.get('size'):
            reasons.append('Unknown disk size')
        descendants = [(n, c) for n, c in roots if c[:len(chain)] == chain]
        if any(n.get('mountpoints') and any(x for x in n['mountpoints']) for n, _ in descendants):
            reasons.append('Target or partition is mounted')
        if any(n.get('fstype') == 'swap' for n, _ in descendants):
            reasons.append('Target contains active or configured swap')
    # Global system mount roots: avoid considering any ancestor disk of /, /home or EFI as a target.
    for n, chain in roots:
        mps = n.get('mountpoints') or []
        if any(m in ('/', '/home', '/boot', '/boot/efi') for m in mps if m):
            if target in chain:
                reasons.append('Target contains system partition')
    # Even a passing assessment is not permission to write: no privileged backend exists.
    return {'allowed_to_write': False, 'read_only': True,
            'candidate_checks_passed': not reasons, 'reasons': reasons,
            'warning': 'Snapshot can become stale; privileged writer must revalidate device identity and mounts'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--target', required=True)
    parser.add_argument('--snapshot', help='Optional JSON fixture; otherwise runs read-only lsblk')
    args = parser.parse_args()
    if args.snapshot:
        with open(args.snapshot, encoding='utf-8') as f:
            data = json.load(f)
    else:
        cp = subprocess.run(['lsblk', '--json', '--bytes', '--paths', '-o',
                             'NAME,PATH,TYPE,TRAN,SIZE,MOUNTPOINTS,FSTYPE'],
                            check=True, capture_output=True, text=True, timeout=10)
        data = json.loads(cp.stdout)
    print(json.dumps(assess(data, args.target), indent=2))


if __name__ == '__main__':
    main()
