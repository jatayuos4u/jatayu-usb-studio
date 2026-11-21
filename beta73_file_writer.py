"""Beta 73: regular-file-only streaming writer laboratory. NOT a USB writer.

The caller supplies an existing, empty private directory (mode 0700), a regular
source file, and a NEW basename. No block devices, symlinks, overwrite, or root.
"""
import hashlib
import os
import stat
from pathlib import Path

CHUNK = 1024 * 1024

class Cancelled(Exception):
    pass

def _regular(fd):
    info = os.fstat(fd)
    if not stat.S_ISREG(info.st_mode):
        raise ValueError('Only regular files are supported')
    return info

def copy_verify(source, destination_dir, basename, progress=None, cancelled=None):
    if os.geteuid() == 0:
        raise PermissionError('Refusing to run as root')
    if not isinstance(basename, str) or basename in ('', '.', '..') or '/' in basename or '\x00' in basename:
        raise ValueError('Destination must be a single filename')
    directory = Path(destination_dir)
    dfd = os.open(directory, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC)
    srcfd = -1
    outfd = -1
    created = False
    output_identity = None
    try:
        di = os.fstat(dfd)
        if di.st_uid != os.geteuid() or stat.S_IMODE(di.st_mode) != 0o700:
            raise PermissionError('Destination directory must be owned by caller and mode 0700')
        if os.listdir(dfd):
            raise ValueError('Destination directory must be empty')
        srcfd = os.open(source, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK | os.O_CLOEXEC)
        si = _regular(srcfd)
        if si.st_size <= 0:
            raise ValueError('Source must not be empty')
        if si.st_size > 16 * 1024**3:
            raise ValueError('Laboratory source size limit is 16 GiB')
        outfd = os.open(basename, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC, 0o600, dir_fd=dfd)
        created = True
        output_identity = os.fstat(outfd)
        h = hashlib.sha256()
        done = 0
        while True:
            if cancelled and cancelled():
                raise Cancelled('Copy cancelled')
            chunk = os.read(srcfd, CHUNK)
            if not chunk:
                break
            h.update(chunk)
            view = memoryview(chunk)
            while view:
                written = os.write(outfd, view)
                if written <= 0:
                    raise OSError('Short write')
                view = view[written:]
            done += len(chunk)
            if progress:
                progress(done, si.st_size)
        after = os.fstat(srcfd)
        if (done != si.st_size or after.st_size != si.st_size or
                (after.st_dev, after.st_ino, after.st_mtime_ns, after.st_ctime_ns) !=
                (si.st_dev, si.st_ino, si.st_mtime_ns, si.st_ctime_ns)):
            raise ValueError('Source changed during copy')
        # Independently reread source to detect in-place changes that do not alter size.
        os.lseek(srcfd, 0, os.SEEK_SET)
        second = hashlib.sha256()
        while True:
            if cancelled and cancelled():
                raise Cancelled('Copy cancelled during source verification')
            block = os.read(srcfd, CHUNK)
            if not block:
                break
            second.update(block)
        if second.digest() != h.digest():
            raise ValueError('Source contents changed during copy')
        if os.fstat(srcfd).st_mtime_ns != si.st_mtime_ns or os.fstat(srcfd).st_ctime_ns != si.st_ctime_ns:
            raise ValueError('Source changed during verification')
        os.fsync(outfd)
        os.close(outfd)
        outfd = -1
        # Verify the destination independently through the already trusted directory fd.
        verifyfd = os.open(basename, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC, dir_fd=dfd)
        try:
            vi = _regular(verifyfd)
            if (vi.st_dev, vi.st_ino) != (output_identity.st_dev, output_identity.st_ino):
                raise ValueError('Destination was replaced')
            if vi.st_size != done:
                raise ValueError('Destination size mismatch')
            check = hashlib.sha256()
            while True:
                chunk = os.read(verifyfd, CHUNK)
                if not chunk:
                    break
                check.update(chunk)
            if check.digest() != h.digest():
                raise ValueError('SHA-256 mismatch')
            # Confirm that verification did not race an output mutation.
            latest = os.fstat(verifyfd)
            if (latest.st_size != vi.st_size or latest.st_mtime_ns != vi.st_mtime_ns or latest.st_ctime_ns != vi.st_ctime_ns):
                raise ValueError('Destination changed during verification')
        finally:
            os.close(verifyfd)
        return {'bytes': done, 'sha256': h.hexdigest(), 'verified': True, 'physical_usb_writing': False}
    except BaseException:
        if created:
            try:
                # Never unlink an attacker-replaced destination.
                current = os.stat(basename, dir_fd=dfd, follow_symlinks=False)
                if output_identity and (current.st_dev, current.st_ino) == (output_identity.st_dev, output_identity.st_ino):
                    os.unlink(basename, dir_fd=dfd)
            except OSError:
                pass
        raise
    finally:
        if outfd >= 0:
            os.close(outfd)
        if srcfd >= 0:
            os.close(srcfd)
        os.close(dfd)
