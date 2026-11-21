"""UDisks2 system-bus Unix-FD acquisition proof-of-integration.

No CLI or GUI writing entry point is exposed here. The obtained descriptor is
READ-ONLY and immediately closed. Never run the whole GUI as root.
"""
import os
import stat
from udisks2_backend import object_path, inspect_usb, DeviceRejected

class AuthorizationUnavailable(RuntimeError):
    pass

def request_readonly_fd(device, *, inspect=inspect_usb, opener=None):
    """Ask UDisks2 for a read-only Unix FD and bind it to the inspected device.

    UDisks2's Block.OpenDevice uses a Unix FD return and is not equivalent to
    busctl's ordinary call interface. Gio must be present on the target host.
    """
    object_path(device)
    evidence = inspect(device)
    if evidence.get('device') != device or evidence.get('status') != 'READ_ONLY_INSPECTED':
        raise DeviceRejected('Untrusted topology result')
    if opener is None:
        opener = _gio_open_readonly
    fd = opener(device)
    try:
        st = os.fstat(fd)
        if not stat.S_ISBLK(st.st_mode):
            raise DeviceRejected('UDisks2 returned a non-block descriptor')
        path_st = os.stat(device, follow_symlinks=False)
        if not stat.S_ISBLK(path_st.st_mode) or path_st.st_rdev != st.st_rdev:
            raise DeviceRejected('Opened descriptor does not match target')
        # Recheck after obtaining the descriptor; still not sufficient to authorize writes.
        again = inspect(device)
        if again != evidence:
            raise DeviceRejected('Device topology changed while acquiring descriptor')
        return {'device':device,'major':os.major(st.st_rdev),'minor':os.minor(st.st_rdev),
                'capacity':evidence['size_bytes'],'write_authorized':False}
    finally:
        os.close(fd)

def _gio_open_readonly(device):
    try:
        import gi
        gi.require_version('Gio','2.0')
        from gi.repository import Gio, GLib
    except (ImportError, ValueError) as exc:
        raise AuthorizationUnavailable('python3-gi/Gio is required') from exc
    connection = Gio.bus_get_sync(Gio.BusType.SYSTEM, None)
    params = GLib.Variant('(sa{sv})', ('r', {}))
    try:
        reply, fd_list = connection.call_with_unix_fd_list_sync(
            'org.freedesktop.UDisks2', object_path(device),
            'org.freedesktop.UDisks2.Block', 'OpenDevice', params,
            GLib.VariantType.new('(h)'), Gio.DBusCallFlags.NONE, 30000, None, None)
    except GLib.Error as exc:
        raise AuthorizationUnavailable('UDisks2 OpenDevice failed or was denied') from exc
    if fd_list is None:
        raise AuthorizationUnavailable('UDisks2 did not return a Unix FD list')
    handle = reply.unpack()[0]
    if not isinstance(handle,int) or handle < 0:
        raise AuthorizationUnavailable('Invalid UDisks2 FD handle')
    try:
        return fd_list.get(handle)  # duplicated fd owned by caller
    except (GLib.Error, IndexError) as exc:
        raise AuthorizationUnavailable('Cannot resolve UDisks2 FD handle') from exc
