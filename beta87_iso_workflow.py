"""Beta87 non-destructive ISO workflow. Regular files only; NEVER a block-device writer.

The workflow produces a verified regular-file image inside a caller-owned private
empty directory. It is deliberately separate from all USB/device authorization.
"""
import hashlib
import os
import stat
from pathlib import Path
from beta73_file_writer import copy_verify, Cancelled

class WorkflowError(Exception):
    pass

def _hash_regular_file(path, progress=None, cancelled=None):
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK | os.O_CLOEXEC)
    try:
        before = os.fstat(fd)
        if not stat.S_ISREG(before.st_mode) or before.st_size <= 0:
            raise WorkflowError('Input must be a nonempty regular file')
        if before.st_size > 16 * 1024**3:
            raise WorkflowError('Input exceeds laboratory size limit')
        digest = hashlib.sha256()
        count = 0
        while True:
            if cancelled and cancelled():
                raise Cancelled('Cancelled while hashing input')
            data = os.read(fd, 1024 * 1024)
            if not data:
                break
            digest.update(data)
            count += len(data)
            if progress:
                progress('hash', count, before.st_size)
        after = os.fstat(fd)
        if (count != before.st_size or
            (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns, before.st_ctime_ns) !=
            (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns, after.st_ctime_ns)):
            raise WorkflowError('Input changed during hashing')
        return digest.hexdigest(), count
    finally:
        os.close(fd)

def stage_iso_file(source, private_empty_directory, *, basename='staged-image.iso', progress=None, cancelled=None):
    """Hash, stage, independently verify, and report result; never access a USB disk."""
    if os.geteuid() == 0:
        raise PermissionError('Never run the file laboratory as root')
    source = Path(source)
    expected, size = _hash_regular_file(source, progress, cancelled)
    def on_copy(done, total):
        if progress:
            progress('copy', done, total)
    result = copy_verify(source, private_empty_directory, basename,
                         progress=on_copy, cancelled=cancelled)
    if result['sha256'] != expected or result['bytes'] != size or not result['verified']:
        # The output must never be represented as a successful staged image.
        raise WorkflowError('Staged image does not match the independently hashed input')
    if progress:
        progress('verified', size, size)
    return {'status': 'VERIFIED_FILE_ONLY', 'bytes': size, 'sha256': expected,
            'staged_path': str(Path(private_empty_directory) / basename),
            'physical_usb_writing': False, 'write_authorized': False}
