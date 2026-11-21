"""Kernel usage checks and private image staging shared by USB Studio."""
import errno
from contextlib import suppress
import hashlib
import os
from pathlib import Path
import stat
import tempfile

from privileged_writer_contract import revalidate


class UnsafeTarget(Exception):
    pass


class WriteCancelled(UnsafeTarget):
    pass


def reject_active_swap(devices, *, swaps_text=None, stat_device=os.stat):
    """Fail closed when the target disk or a partition backs active swap.

    /proc/self/mountinfo does not include swap devices. Only canonical device
    nodes are accepted for comparison; malformed swap entries fail closed.
    """
    content = Path('/proc/swaps').read_text() if swaps_text is None else swaps_text
    lines = content.splitlines()
    if not lines or not lines[0].startswith('Filename'):
        raise UnsafeTarget('Cannot verify active swap devices')
    for line in lines[1:]:
        columns = line.split()
        if len(columns) < 2:
            raise UnsafeTarget('Malformed active swap record')
        source, kind = columns[:2]
        if kind not in ('partition', 'file') or not source.startswith('/'):
            raise UnsafeTarget('Unknown active swap backing type')
        source = source.replace(r'\040', ' ').replace(r'\011', '\t').replace(r'\134', '\\')
        try:
            st = stat_device(source)
        except OSError as exc:
            raise UnsafeTarget('Cannot identify active swap device') from exc
        if kind == 'partition':
            if not stat.S_ISBLK(st.st_mode):
                raise UnsafeTarget('Unexpected active swap device type')
            backing = st.st_rdev
        else:
            if not stat.S_ISREG(st.st_mode):
                raise UnsafeTarget('Unexpected active swap file type')
            backing = st.st_dev
        if (os.major(backing), os.minor(backing)) in devices:
            raise UnsafeTarget('Target disk or partition is active swap')


def validate_target(path, identity, *, sys_root=Path('/sys'), mountinfo=None):
    if identity.path != path or identity.transport != 'usb':
        raise UnsafeTarget('Not the inspected USB target')
    node = sys_root/'class/block'/path.removeprefix('/dev/')
    if (node/'removable').read_text().strip() != '1':
        raise UnsafeTarget('Non-removable disk blocked')
    if (node/'ro').read_text().strip() != '0':
        raise UnsafeTarget('Read-only disk blocked')
    if (node/'holders').exists() and any((node/'holders').iterdir()):
        raise UnsafeTarget('Disk has active holders')
    parts = []
    for item in node.iterdir():
        if (item/'partition').exists():
            if (item/'holders').exists() and any((item/'holders').iterdir()):
                raise UnsafeTarget('Partition has active holders')
            parts.append(item)
    nums={(identity.major,identity.minor)}
    for item in parts:
        a,b=(item/'dev').read_text().strip().split(':')
        nums.add((int(a),int(b)))
    content = Path('/proc/self/mountinfo').read_text() if mountinfo is None else mountinfo
    for line in content.splitlines():
        fields=line.split()
        if len(fields)<6:raise UnsafeTarget('Malformed mount information')
        a,b=fields[2].split(':')
        if (int(a),int(b)) in nums:raise UnsafeTarget('Mounted disk or partition')
    reject_active_swap(nums)
    if not revalidate(identity):raise UnsafeTarget('Device identity changed')
    return True

def snapshot_locations(size):
    directories = tuple(dict.fromkeys((Path(tempfile.gettempdir()), Path.home())))
    for directory in directories:
        try:
            space = os.statvfs(directory)
        except OSError:
            continue
        if space.f_bavail * space.f_frsize >= size:
            yield directory


def snapshot_space_error(size, operation):
    checked = ', '.join(dict.fromkeys((tempfile.gettempdir(), str(Path.home()))))
    return UnsafeTarget(f'{operation} needs {size:,} bytes of free, writable space. '
                        f'Checked {checked}. Free space there and retry. '
                        'No data was written to the target USB.')


def open_iso_snapshot(size):
    """Choose a filesystem with enough room for an unlinked ISO snapshot."""
    for directory in snapshot_locations(size):
        try:
            return tempfile.TemporaryFile(mode='w+b', dir=directory), directory
        except OSError:
            continue
    raise snapshot_space_error(size, 'ISO staging')


def stage_iso_verified(iso, *, max_bytes, chunk=1024*1024, cancelled=lambda: False, progress=None, preflight=None):
    """Copy source to a private unlinked regular-file snapshot before target is opened.

    Caller owns returned file object. The original ISO is never read after staging.
    This mitigates source-path mutation, but does NOT authorize block-device writes.
    """
    if chunk <= 0 or max_bytes <= 0:
        raise UnsafeTarget('Invalid staging bounds')
    flags = os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC | getattr(os, 'O_NONBLOCK', 0)
    fd = os.open(iso, flags)
    try:
        st = os.fstat(fd)
        if not stat.S_ISREG(st.st_mode) or not 0 < st.st_size <= max_bytes:
            raise UnsafeTarget('ISO is invalid or too large')
        if cancelled():
            raise WriteCancelled('Cancelled during ISO staging')
        if preflight is not None:
            with os.fdopen(os.dup(fd), 'rb') as source:
                preflight(source, st.st_size)
        snapshot, directory = open_iso_snapshot(st.st_size)
        try:
            digest = hashlib.sha256()
            total = 0
            while total < st.st_size:
                if cancelled():
                    raise WriteCancelled('Cancelled during ISO staging')
                buf = os.read(fd, min(chunk, st.st_size-total))
                if not buf:
                    raise UnsafeTarget('ISO truncated during staging')
                snapshot.write(buf)
                digest.update(buf)
                total += len(buf)
                if progress:
                    progress(total, st.st_size)
            after = os.fstat(fd)
            if (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns, after.st_ctime_ns) != (st.st_dev, st.st_ino, st.st_size, st.st_mtime_ns, st.st_ctime_ns):
                raise UnsafeTarget('ISO metadata changed during staging')
            snapshot.flush()
            snapshot.seek(0)
            return snapshot, digest.hexdigest(), total
        except OSError as exc:
            with suppress(OSError):
                snapshot.close()
            if exc.errno in (errno.ENOSPC, errno.EDQUOT):
                raise UnsafeTarget(f'ISO staging ran out of space or exceeded a quota in {directory}. '
                                   'Free space there and retry. No data was written to the target USB.') from exc
            raise
        except BaseException:
            snapshot.close()
            raise
    finally:
        os.close(fd)

