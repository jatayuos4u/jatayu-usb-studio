"""Fail-closed UDisks2 writable-FD boundary prototype.

This module NEVER writes, erases or returns a writable FD to callers. It
requests a writable descriptor (which may trigger Polkit), attests its device
identity, then closes it. GUI integration is intentionally disabled pending
security review and hardware tests.
"""
import os
import stat
import fcntl
from udisks2_backend import object_path, inspect_usb, DeviceRejected
from udisks2_fd_backend import AuthorizationUnavailable


class WriteBoundaryRejected(RuntimeError):
    pass


def _open_via_udisks(device):
    try:
        import gi
        gi.require_version('Gio', '2.0')
        from gi.repository import Gio, GLib
    except (ImportError, ValueError) as exc:
        raise AuthorizationUnavailable('Gio is required') from exc
    bus = Gio.bus_get_sync(Gio.BusType.SYSTEM, None)
    try:
        reply, fd_list = bus.call_with_unix_fd_list_sync(
            'org.freedesktop.UDisks2', object_path(device),
            'org.freedesktop.UDisks2.Block', 'OpenDevice',
            GLib.Variant('(sa{sv})', ('rw', {})), GLib.VariantType.new('(h)'),
            Gio.DBusCallFlags.NONE, 30000, None, None)
    except GLib.Error as exc:
        raise AuthorizationUnavailable('UDisks2 authorization denied or unavailable') from exc
    if fd_list is None:
        raise AuthorizationUnavailable('Missing Unix FD list')
    handle = reply.unpack()[0]
    if not isinstance(handle, int) or handle < 0:
        raise AuthorizationUnavailable('Invalid FD handle')
    try:
        return fd_list.get(handle)
    except (GLib.Error, IndexError) as exc:
        raise AuthorizationUnavailable('Invalid Unix FD handle') from exc


def inspect_writable_boundary(device, *, inspect=inspect_usb, opener=None):
    """Acquire, validate and immediately close a UDisks2 FD; never write.

    This is NOT sufficient to authorize a destructive operation: mount-state
    and identity may change, and no write service/GUI flow is implemented.
    """
    object_path(device)
    before = inspect(device)
    if before.get('device') != device or before.get('status') != 'READ_ONLY_INSPECTED':
        raise DeviceRejected('Untrusted inspection evidence')
    fd = (opener or _open_via_udisks)(device)
    try:
        st = os.fstat(fd)
        if not stat.S_ISBLK(st.st_mode):
            raise WriteBoundaryRejected('Descriptor is not a block device')
        if (fcntl.fcntl(fd, fcntl.F_GETFL) & os.O_ACCMODE) != os.O_RDWR:
            raise WriteBoundaryRejected('Descriptor is not writable')
        target = os.stat(device, follow_symlinks=False)
        if not stat.S_ISBLK(target.st_mode) or target.st_rdev != st.st_rdev:
            raise WriteBoundaryRejected('Descriptor does not match target')
        after = inspect(device)
        if after != before:
            raise WriteBoundaryRejected('Topology changed during authorization')
        return {'status': 'WRITABLE_FD_ATTESTED_AND_CLOSED',
                'device': device, 'major': os.major(st.st_rdev),
                'minor': os.minor(st.st_rdev), 'writing_enabled': False,
                'write_authorized': False}
    finally:
        os.close(fd)
