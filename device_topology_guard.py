"""Beta 34: read-only, fail-closed topology risk preview. NEVER authorizes writes.

Caller supplies an independently captured lsblk --json --bytes --output
NAME,PATH,TYPE,TRAN,RM,RO,SIZE,MOUNTPOINTS,PKNAME snapshot. This is
advisory only: a privileged worker must independently validate the open
block descriptor, major/minor, sysfs topology and mounts at operation time.
"""
import json

MAX_BYTES = 1024 * 1024


def _fail(reason):
    return {"ok": False, "authorized": False, "writing_enabled": False, "reason": reason}


def inspect_topology(snapshot, target):
    if not isinstance(target, str) or not target.startswith('/dev/') or '/' in target[5:]:
        return _fail('Invalid target path')
    if not isinstance(snapshot, (str, bytes)) or len(snapshot) > MAX_BYTES:
        return _fail('Invalid or oversized topology snapshot')
    try:
        data = json.loads(snapshot)
        roots = data['blockdevices']
        if not isinstance(roots, list): raise ValueError('Invalid blockdevices')
        matches = []
        def walk(node, ancestors):
            if not isinstance(node, dict): raise ValueError('Invalid device entry')
            path = node.get('path')
            if not isinstance(path, str): raise ValueError('Missing device path')
            if path == target: matches.append((node, ancestors))
            children = node.get('children', [])
            if not isinstance(children, list): raise ValueError('Invalid children')
            for child in children: walk(child, ancestors + (node,))
        for root in roots: walk(root, ())
        if len(matches) != 1: return _fail('Target missing or ambiguous')
        disk, ancestors = matches[0]
        if ancestors or disk.get('type') != 'disk': return _fail('Whole disk required')
        if disk.get('tran') != 'usb' or disk.get('rm') not in (True, 1):
            return _fail('USB removable transport not established')
        if disk.get('ro') not in (False, 0): return _fail('Read-only or unknown disk state')
        if type(disk.get('size')) is not int or disk['size'] <= 0: return _fail('Unknown disk size')
        if disk.get('pkname') not in (None, ''): return _fail('Unexpected parent device')
        devices = []
        def gather(node):
            devices.append(node)
            for child in node.get('children', []): gather(child)
        gather(disk)
        for item in devices:
            mounts = item.get('mountpoints')
            if not isinstance(mounts, list): return _fail('Unknown mount state')
            if any(m is not None and m != '' for m in mounts): return _fail('Mounted target or descendant')
            if item.get('type') in ('crypt', 'lvm', 'raid', 'md', 'mpath'):
                return _fail('Complex block topology requires manual review')
        return {"ok": True, "authorized": False, "writing_enabled": False,
                "reason": "Read-only topology preview passed; no authorization granted",
                "partition_count": sum(x.get('type') == 'part' for x in devices[1:])}
    except (ValueError, KeyError, TypeError, RecursionError, UnicodeDecodeError) as exc:
        return _fail('Malformed topology snapshot: ' + str(exc))
