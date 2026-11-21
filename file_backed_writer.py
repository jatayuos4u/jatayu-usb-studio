"""Beta 22: file-to-new-file image copy ONLY. No block-device access.

The destination must be a new regular file in an existing directory. This
module is intentionally not connected to the D-Bus service or KDE GUI.
"""
import hashlib
import os
import stat
import time

CHUNK = 1024 * 1024
MAX_IMAGE = 16 * 1024 ** 3

class CopyCancelled(Exception):
    pass

class UnsafeDestination(ValueError):
    pass

def copy_image_to_new_file(source, destination, *, progress=None, cancelled=None, status=None, clock=None):
    """Copy a regular file into a NEW regular file, hash both streams.

    Returns bytes and SHA-256. Rejects symlinks, existing files, special
    files, and changes in source size. Removes incomplete output on failure.
    Never accepts block devices as a destination.
    """
    if not isinstance(source, (str, os.PathLike)) or not isinstance(destination, (str, os.PathLike)):
        raise TypeError('Paths required')
    source, destination = os.fspath(source), os.fspath(destination)
    if not source or not destination or not os.path.isabs(source) or not os.path.isabs(destination):
        raise ValueError('Absolute paths required')
    if os.path.basename(destination) in ('', '.', '..'):
        raise UnsafeDestination('Invalid destination name')
    parent, name = os.path.split(destination)
    # Never traverse a symlink in the destination directory itself.
    parent_fd = os.open(parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC)
    output_fd = None
    created = False
    output_identity = None
    now = clock if clock is not None else time.monotonic
    started = now()
    def emit(phase, done, total):
        if status is not None:
            elapsed = max(0.0, now() - started)
            status({"phase": phase, "bytes_done": done, "bytes_total": total,
                    "elapsed_seconds": elapsed, "bytes_per_second": done / elapsed if elapsed > 0 else 0.0})
    try:
        with os.fdopen(os.open(source, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK | os.O_CLOEXEC), 'rb') as inp:
            before = os.fstat(inp.fileno())
            if not stat.S_ISREG(before.st_mode) or before.st_size <= 0 or before.st_size > MAX_IMAGE:
                raise ValueError('Source must be a nonempty regular file within size limit')
            if cancelled is not None and cancelled():
                raise CopyCancelled('Cancelled before starting')
            output_fd = os.open(name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC, 0o600, dir_fd=parent_fd)
            created = True
            output_stat = os.fstat(output_fd)
            output_identity = (output_stat.st_dev, output_stat.st_ino)
            h = hashlib.sha256()
            count = 0
            with os.fdopen(output_fd, 'wb', closefd=True) as out:
                output_fd = None
                while True:
                    if cancelled is not None and cancelled():
                        raise CopyCancelled('Copy cancelled')
                    block = inp.read(min(CHUNK, before.st_size - count))
                    if not block:
                        break
                    out.write(block)
                    h.update(block)
                    count += len(block)
                    if progress is not None:
                        progress(count, before.st_size)
                    emit("copy", count, before.st_size)
                out.flush()
                os.fsync(out.fileno())
            after = os.fstat(inp.fileno())
            if count != before.st_size or (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns) != (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns):
                raise IOError('Source changed while copying')
            # Read-back verification detects corruption in the destination.
            verify = hashlib.sha256()
            verified_count = 0
            verify_fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC, dir_fd=parent_fd)
            with os.fdopen(verify_fd, 'rb') as check:
                if not stat.S_ISREG(os.fstat(check.fileno()).st_mode):
                    raise IOError('Destination is not regular')
                while True:
                    if cancelled is not None and cancelled():
                        raise CopyCancelled('Verification cancelled')
                    block = check.read(CHUNK)
                    if not block:
                        break
                    verify.update(block)
                    verified_count += len(block)
                    emit('verify', verified_count, before.st_size)
            # Check the directory entry still names the file we created.
            entry_stat = os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
            if not stat.S_ISREG(entry_stat.st_mode) or (entry_stat.st_dev, entry_stat.st_ino) != output_identity:
                raise IOError('Destination replaced during verification')
            if verified_count != count:
                raise IOError('Read-back length mismatch')
            if cancelled is not None and cancelled():
                raise CopyCancelled('Verification cancelled')
            if verify.digest() != h.digest():
                raise IOError('Read-back verification failed')
            final_source = os.stat(source, follow_symlinks=False)
            if (final_source.st_dev, final_source.st_ino, final_source.st_size, final_source.st_mtime_ns) != (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns):
                raise IOError('Source changed during verification')
            # Re-read the source contents: timestamps may not change on
            # filesystems with coarse timestamp granularity. Metadata alone
            # cannot detect same-size, in-place modifications.
            source_check = hashlib.sha256()
            inp.seek(0)
            source_check_count = 0
            while True:
                if cancelled is not None and cancelled():
                    raise CopyCancelled('Source recheck cancelled')
                block = inp.read(CHUNK)
                if not block:
                    break
                source_check.update(block)
                source_check_count += len(block)
            if source_check_count != count or source_check.digest() != h.digest():
                raise IOError('Source content changed during operation')
            final_source_fd = os.fstat(inp.fileno())
            if (final_source_fd.st_dev, final_source_fd.st_ino, final_source_fd.st_size,
                    final_source_fd.st_mtime_ns) != (before.st_dev, before.st_ino,
                    before.st_size, before.st_mtime_ns):
                raise IOError('Source changed during recheck')
            emit('complete', count, before.st_size)
            return {'bytes_copied': count, 'sha256': h.hexdigest(), 'verified': True}
    except BaseException:
        if created:
            try:
                current = os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
                if (current.st_dev, current.st_ino) == output_identity:
                    os.unlink(name, dir_fd=parent_fd)
            except OSError:
                pass
        raise
    finally:
        if output_fd is not None:
            os.close(output_fd)
        os.close(parent_fd)
