"""Beta 36 read-only USB identity comparison; never an authorization primitive.

A saved baseline is untrusted and can be stale. A privileged service must use
kernel-backed descriptor checks and revalidate at operation time.
"""
import json
import re
from device_topology_guard import inspect_topology, MAX_BYTES

COLUMNS = 'NAME,PATH,TYPE,TRAN,RM,RO,SIZE,MOUNTPOINTS,PKNAME,MAJ:MIN,SERIAL,WWN,MODEL,VENDOR'
_ID_RE = re.compile(r'^[^\x00-\x1f\x7f]{1,256}$')


def _deny(reason):
    return {'ok': False, 'authorized': False, 'writing_enabled': False, 'read_only': True, 'reason': reason}


def _nodes(snapshot):
    if not isinstance(snapshot, (bytes, str)) or len(snapshot) > MAX_BYTES:
        raise ValueError('Invalid snapshot size')
    obj = json.loads(snapshot)
    roots = obj.get('blockdevices')
    if not isinstance(roots, list):
        raise ValueError('Invalid blockdevices')
    found = []
    def walk(node, depth=0):
        if depth > 32 or not isinstance(node, dict):
            raise ValueError('Invalid device hierarchy')
        found.append(node)
        children = node.get('children', [])
        if not isinstance(children, list):
            raise ValueError('Invalid children')
        for child in children:
            walk(child, depth + 1)
    for node in roots:
        walk(node)
    return found


def capture_identity(snapshot, target):
    """Create a conservative identity baseline from a *live* lsblk snapshot."""
    topology = inspect_topology(snapshot, target)
    if not topology['ok']:
        return _deny('Topology rejected: ' + topology['reason'])
    try:
        matches = [n for n in _nodes(snapshot) if n.get('path') == target]
        if len(matches) != 1:
            return _deny('Missing or ambiguous target')
        disk = matches[0]
        serial, wwn, devnum = disk.get('serial'), disk.get('wwn'), disk.get('maj:min')
        if not any(isinstance(x, str) and x.strip() for x in (serial, wwn)):
            return _deny('No stable hardware serial or WWN; manual review required')
        if not isinstance(devnum, str) or not re.fullmatch(r'\d+:\d+', devnum):
            return _deny('Missing kernel major:minor identifier')
        for value in (serial, wwn):
            if value is not None and (not isinstance(value, str) or (value and not _ID_RE.fullmatch(value))):
                return _deny('Invalid hardware identifier')
        children = sorted((n.get('path'), n.get('type'), n.get('size'), n.get('maj:min'))
                          for n in _nodes(snapshot) if n.get('pkname') == disk.get('name'))
        if any(not isinstance(p, str) or not isinstance(t, str) or type(s) is not int or
               not isinstance(m, str) for p, t, s, m in children):
            return _deny('Incomplete child device identity')
        identity = {'target': target, 'serial': serial or '', 'wwn': wwn or '',
                    'major_minor': devnum, 'size': disk['size'],
                    'model': disk.get('model') or '', 'vendor': disk.get('vendor') or '',
                    'partitions': [list(row) for row in children]}
        return {'ok': True, 'authorized': False, 'writing_enabled': False, 'read_only': True,
                'reason': 'Advisory identity baseline captured; no authorization granted',
                'identity': identity}
    except (ValueError, TypeError, KeyError, RecursionError) as exc:
        return _deny('Invalid identity snapshot: ' + str(exc))


def compare_identity(baseline, fresh_snapshot, target):
    """Fail closed on any identity or partition change, including target renumbering."""
    if not isinstance(baseline, dict) or baseline.get('ok') is not True or not isinstance(baseline.get('identity'), dict):
        return _deny('Invalid baseline')
    fresh = capture_identity(fresh_snapshot, target)
    if not fresh['ok']:
        return fresh
    if baseline['identity'] != fresh['identity']:
        return _deny('USB identity or topology changed since baseline')
    return {'ok': True, 'authorized': False, 'writing_enabled': False, 'read_only': True,
            'reason': 'Advisory identity matches; no authorization granted'}
