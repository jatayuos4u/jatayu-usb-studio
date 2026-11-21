"""Experimental UDisks2 descriptor-bound ISO transaction.

Not exposed in GUI or installed as an executable. Requires separate security
review and disposable-device validation before production activation.
"""
import fcntl
import os
import stat
from contextlib import closing

from beta91_experimental_writer import (UnsafeTarget, inspect_live,
    validate_target, stage_iso_verified, assert_open_target_identity)
from udisks2_backend import inspect_usb, object_path, DeviceRejected
from udisks2_write_boundary import _open_via_udisks
from verified_write_transaction import transfer_and_verify


def authorized_transaction(iso, device, *, confirm, opener=None,
                           inspector=inspect_live, topology=inspect_usb,
                           validator=validate_target, stager=stage_iso_verified,
                           transfer=transfer_and_verify, cancelled=lambda: False,
                           progress=None, identity_check=assert_open_target_identity):
    """Write only after independent checks, staged ISO, and UDisks2 FD binding.

    No root process or direct /dev open. A caller must obtain explicit user
    confirmation; UDisks2 controls authorization. Cancellation after writing
    begins leaves a partially overwritten device.
    """
    object_path(device)
    if confirm != 'ERASE ' + device:
        raise UnsafeTarget('Exact erase confirmation required')
    identity = inspector(device)
    validator(device, identity)
    before = topology(device)
    if before.get('status') != 'READ_ONLY_INSPECTED' or before.get('device') != device:
        raise DeviceRejected('Invalid USB topology evidence')
    if before.get('size_bytes') != identity.size_bytes:
        raise DeviceRejected('Capacity mismatch')
    snapshot, digest, size = stager(iso, max_bytes=identity.size_bytes, cancelled=cancelled)
    try:
        if cancelled():
            raise UnsafeTarget('Cancelled before authorization')
        validator(device, identity)
        if topology(device) != before:
            raise DeviceRejected('USB topology changed before authorization')
        fd = (opener or _open_via_udisks)(device)
        with closing(os.fdopen(fd, 'rb+', buffering=0, closefd=True)) as target:
            raw_fd = target.fileno()
            st = os.fstat(raw_fd)
            if not stat.S_ISBLK(st.st_mode):
                raise UnsafeTarget('Authorized FD is not a block device')
            if (os.major(st.st_rdev), os.minor(st.st_rdev)) != (identity.major, identity.minor):
                raise UnsafeTarget('Authorized FD identity mismatch')
            if fcntl.fcntl(raw_fd, fcntl.F_GETFL) & os.O_ACCMODE != os.O_RDWR:
                raise UnsafeTarget('Authorized FD is not read/write')
            identity_check(raw_fd, identity)
            validator(device, identity)
            if topology(device) != before:
                raise DeviceRejected('USB topology changed after authorization')
            if cancelled():
                raise UnsafeTarget('Cancelled before writing')
            result = transfer(snapshot.fileno(), raw_fd, size,
                              cancelled=cancelled, progress=progress,
                              pre_write_check=lambda opened_fd:
                                  identity_check(opened_fd, identity) and
                                  validator(device, identity) and
                                  topology(device) == before)
            if result.get('sha256') != digest:
                raise UnsafeTarget('Staged ISO digest mismatch')
            return result
    finally:
        snapshot.close()
