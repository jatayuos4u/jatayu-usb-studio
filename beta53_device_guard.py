"""Beta 53: read-only device identity policy and TOCTOU detection.

This module does not open block devices and cannot authorize writes.
"""
import os
import stat

class DeviceChanged(Exception):
    pass

def validate_snapshot(before, after):
    """Fail closed if a live device differs from the captured baseline."""
    required=('path','major_minor','size','serial','model','vendor','transport','partitions')
    if not isinstance(before,dict) or not isinstance(after,dict):
        raise DeviceChanged('Missing device snapshots')
    for key in required:
        if key not in before or key not in after or before[key] != after[key]:
            raise DeviceChanged('Device changed or identity incomplete: '+key)
    if not isinstance(before['path'],str) or not before['path'].startswith('/dev/'):
        raise DeviceChanged('Invalid device path')
    if not isinstance(before['size'],int) or isinstance(before['size'],bool) or before['size'] <= 0:
        raise DeviceChanged('Invalid device capacity')
    if not isinstance(before['partitions'],list):
        raise DeviceChanged('Invalid partition snapshot')
    return {'matched':True,'authorized':False,'writing_enabled':False}

def verify_regular_file_only(path):
    """Safe test-target check. Reject symlinks and every special file."""
    info=os.lstat(path)
    if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
        raise DeviceChanged('Not a single-link regular file')
    return {'regular_file':True,'authorized':False,'writing_enabled':False}
