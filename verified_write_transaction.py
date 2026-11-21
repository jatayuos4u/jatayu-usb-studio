"""Descriptor-bound write/readback transaction, independent of authorization.

The caller MUST obtain and validate an authorized target descriptor and perform
live target/topology checks before calling this module. No block device is opened
here. This module is not a standalone hardware writer.
"""
import hashlib
import os
from studio_device_safety import UnsafeTarget, WriteCancelled


def transfer_and_verify(source_fd, target_fd, size, *, chunk=1024 * 1024,
                        cancelled=lambda: False, progress=None,
                        pre_write_check=None, target_offset=0, source_offset=0, liveness_check=None):
    """Write exactly size bytes, fsync, then verify readback on the same FD.

    Both descriptors must be opened by the caller. The target is never closed
    here. On any failure, its contents may be partially overwritten.
    """
    if not isinstance(size, int) or isinstance(size, bool) or size <= 0 or chunk <= 0:
        raise UnsafeTarget('Invalid transfer size')
    if not isinstance(target_offset, int) or target_offset < 0:
        raise UnsafeTarget('Invalid destination offset')
    if pre_write_check is None:
        raise UnsafeTarget('Live pre-write target attestation required')
    if not pre_write_check(target_fd):
        raise UnsafeTarget('Live target attestation rejected')
    if cancelled():
        raise WriteCancelled('Cancelled before write')
    os.lseek(source_fd, source_offset, os.SEEK_SET)
    os.lseek(target_fd, target_offset, os.SEEK_SET)
    digest = hashlib.sha256()
    done = 0
    pending = False
    last_sync = 0
    try:
        while done < size:
            if liveness_check:
                liveness_check()
            if cancelled():
                raise WriteCancelled('Cancelled during write; target may be partially overwritten')
            block = os.read(source_fd, min(chunk, size - done))
            if not block:
                raise UnsafeTarget('Source truncated')
            digest.update(block)
            view = memoryview(block)
            while view:
                if cancelled():
                    raise WriteCancelled('Cancelled during write; target may be partially overwritten')
                n = os.write(target_fd, view)
                if n <= 0:
                    raise UnsafeTarget('Write returned no data')
                pending = True
                view = view[n:]
            done += len(block)
            # Bound the amount of dirty data left to flush after Cancel.
            if done - last_sync >= 16 * 1024 * 1024:
                os.fsync(target_fd)
                pending = False
                last_sync = done
            if progress:
                progress('write', done, size)
    finally:
        if pending:
            os.fsync(target_fd)
    if hasattr(os, 'posix_fadvise'):
        # Ask the kernel to discard cached pages before the verification read.
        os.posix_fadvise(target_fd, target_offset, size, os.POSIX_FADV_DONTNEED)
    os.lseek(target_fd, target_offset, os.SEEK_SET)
    actual = hashlib.sha256()
    done = 0
    while done < size:
        if liveness_check:
            liveness_check()
        if cancelled():
            raise WriteCancelled('Cancelled during verification; target already overwritten')
        block = os.read(target_fd, min(chunk, size - done))
        if not block:
            raise UnsafeTarget('Readback truncated')
        actual.update(block)
        done += len(block)
        if progress:
            progress('verify', done, size)
    if actual.digest() != digest.digest():
        raise UnsafeTarget('SHA-256 readback mismatch')
    return {'status': 'WRITTEN_AND_VERIFIED', 'bytes': size, 'sha256': digest.hexdigest()}
