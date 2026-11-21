"""Fail-closed, non-writing hardware preflight for a future privileged writer.

Not a security authorization; never opens a device for writing.
"""
import os
import stat
from pathlib import Path
from privileged_writer_contract import inspect_live

class PreflightRejected(ValueError):
    pass

def validate_target(path, *, inspector=inspect_live, mountinfo=None, sysroot=Path('/sys')):
    if not isinstance(path, str) or not path.startswith('/dev/') or '/' in path[5:]:
        raise PreflightRejected('Only direct /dev disk paths are accepted')
    try:
        identity = inspector(path)
        if identity.path != path or identity.transport != 'usb' or identity.size_bytes <= 0:
            raise PreflightRejected('Device identity or USB transport mismatch')
        name = path[5:]
        node = sysroot / 'class/block' / name
        if not node.exists() or (node/'partition').exists():
            raise PreflightRejected('Missing whole-disk sysfs identity')
        removable = (node/'removable').read_text().strip()
        if removable != '1':
            raise PreflightRejected('Device not marked removable')
        children = [p.name for p in node.iterdir() if (p/'partition').exists()]
        mounted = mountinfo if mountinfo is not None else Path('/proc/self/mountinfo').read_text()
        devs = {(identity.major,identity.minor)}
        for child in children:
            major, minor = (node/child/'dev').read_text().strip().split(':')
            devs.add((int(major),int(minor)))
        for line in mounted.splitlines():
            fields=line.split()
            if len(fields) < 5:
                raise PreflightRejected('Malformed mount information')
            mm=fields[2].split(':')
            if len(mm)!=2:
                raise PreflightRejected('Malformed mount device number')
            if (int(mm[0]),int(mm[1])) in devs:
                raise PreflightRejected('Target or partition is mounted')
        if not children:
            # A blank removable drive may have no partitions.
            pass
        return {'status':'PREFLIGHT_ONLY','path':path,'size_bytes':identity.size_bytes,
                'major':identity.major,'minor':identity.minor,
                'serial':identity.serial,'sysfs_path':identity.sysfs_path,
                'writing_enabled':False,'authorized':False}
    except (OSError, TypeError, AttributeError, IndexError) as e:
        raise PreflightRejected('Incomplete hardware or mount evidence') from e
