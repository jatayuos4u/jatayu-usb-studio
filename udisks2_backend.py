"""Read-only UDisks2 boundary and target attestation.

No method in this module opens or writes block devices.  This is NOT a
privileged writer or a substitute for authorization at write time.
"""
import json
import re
import subprocess

class BackendUnavailable(RuntimeError):
    pass

class DeviceRejected(ValueError):
    pass

_BLOCK = re.compile(r'^/dev/(sd[a-z]+|nvme\d+n\d+|mmcblk\d+)$')

def object_path(device):
    if not isinstance(device, str) or not _BLOCK.fullmatch(device):
        raise ValueError('Expected canonical whole-disk /dev path')
    return '/org/freedesktop/UDisks2/block_devices/' + device[5:]

def probe(*, runner=subprocess.run):
    command = ['busctl', '--system', '--no-pager', 'get-property',
               'org.freedesktop.UDisks2', '/org/freedesktop/UDisks2/Manager',
               'org.freedesktop.UDisks2.Manager', 'Version']
    try:
        result = runner(command, capture_output=True, text=True, timeout=4, check=False)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {'available': False, 'writing_enabled': False, 'reason': type(exc).__name__}
    if result.returncode != 0:
        return {'available': False, 'writing_enabled': False, 'reason': 'Service not reachable'}
    return {'available': True, 'writing_enabled': False,
            'reason': 'Read-only capability probe; authorized writer not integrated'}

def inspect_usb(device, *, runner=subprocess.run):
    """Fail-closed read-only topology inspection; never authorizes writing.

    Reject any descendant mounted anywhere, including swap and root topology.
    A privileged backend must independently recheck all evidence and the opened
    descriptor immediately before an authorized write.
    """
    object_path(device)
    cmd = ['lsblk', '--json', '--bytes', '--paths', '--output',
           'NAME,TYPE,TRAN,RM,RO,SIZE,MOUNTPOINTS,PKNAME', device]
    try:
        result = runner(cmd, capture_output=True, text=True, timeout=5, check=False)
        if result.returncode != 0:
            raise DeviceRejected('Unable to inspect target')
        data = json.loads(result.stdout)
        roots = data['blockdevices']
        if not isinstance(roots, list) or len(roots) != 1:
            raise DeviceRejected('Ambiguous target topology')
        root = roots[0]
        if root.get('name') != device or root.get('type') != 'disk':
            raise DeviceRejected('Target is not a whole disk')
        if root.get('tran') != 'usb' or root.get('rm') not in (True, 1, '1'):
            raise DeviceRejected('Target is not a removable USB disk')
        if root.get('ro') not in (False, 0, '0'):
            raise DeviceRejected('Target is read-only or status unknown')
        size = root.get('size')
        if isinstance(size, bool) or not isinstance(size, int) or size <= 0:
            raise DeviceRejected('Invalid device capacity')
        seen = set()
        def walk(node):
            name = node.get('name')
            if not isinstance(name, str) or name in seen or not name.startswith('/dev/'):
                raise DeviceRejected('Ambiguous child topology')
            seen.add(name)
            mounts = node.get('mountpoints')
            if not isinstance(mounts, list) or any(m is not None for m in mounts):
                raise DeviceRejected('Mounted or unknown filesystem state')
            for child in node.get('children', []):
                if not isinstance(child, dict):
                    raise DeviceRejected('Invalid child topology')
                walk(child)
        walk(root)
        return {'device': device, 'size_bytes': size, 'descendants': len(seen)-1,
                'status': 'READ_ONLY_INSPECTED', 'authorized': False,
                'writing_enabled': False}
    except (OSError, subprocess.TimeoutExpired, ValueError, TypeError, KeyError) as exc:
        if isinstance(exc, DeviceRejected):
            raise
        raise DeviceRejected('Incomplete or unavailable topology evidence') from exc

if __name__ == '__main__':
    print(json.dumps(probe()))
