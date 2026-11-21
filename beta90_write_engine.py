"""File-backed write/readback engine. NEVER opens a physical block device.

Development harness only; does not authorize, enable or perform USB writes.
"""
import hashlib
import os
import stat
from pathlib import Path

class WriteRejected(Exception): pass
class WriteCancelled(WriteRejected): pass

def copy_and_verify(source, destination, *, progress=None, cancelled=None, chunk_size=1024*1024):
    """Create a NEW regular output file, write, fsync and verify by readback.

    Caller must supply a fresh destination under a trusted, non-symlink parent.
    Destination is not removed on failure so partial output remains visible.
    """
    if not isinstance(chunk_size,int) or not 4096 <= chunk_size <= 8*1024*1024:
        raise WriteRejected('Invalid chunk size')
    src=Path(source); dst=Path(destination)
    if dst.exists() or dst.is_symlink() or dst.parent.is_symlink() or not dst.parent.is_dir():
        raise WriteRejected('Destination must be a new file under a real directory')
    if src.is_symlink(): raise WriteRejected('Symlink ISO forbidden')
    if os.path.realpath(src)==os.path.realpath(dst): raise WriteRejected('Source and destination match')
    src_fd=None;dst_fd=None
    try:
        src_fd=os.open(src,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK|os.O_CLOEXEC)
        st=os.fstat(src_fd)
        if not stat.S_ISREG(st.st_mode) or st.st_size<=0:
            raise WriteRejected('Source must be a nonempty regular file')
        dst_fd=os.open(dst,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW|os.O_CLOEXEC,0o600)
        if not stat.S_ISREG(os.fstat(dst_fd).st_mode):
            raise WriteRejected('Destination must be a regular file')
        digest=hashlib.sha256(); total=0
        while True:
            if cancelled and cancelled(): raise WriteCancelled('Cancelled during copy')
            block=os.read(src_fd,chunk_size)
            if not block: break
            view=memoryview(block)
            while view:
                if cancelled and cancelled(): raise WriteCancelled('Cancelled during write')
                n=os.write(dst_fd,view)
                if n<=0: raise WriteRejected('Short write')
                view=view[n:]
            digest.update(block);total+=len(block)
            if progress: progress('write',total,st.st_size)
        if total!=st.st_size or os.fstat(src_fd).st_size!=st.st_size:
            raise WriteRejected('Source size changed')
        os.fsync(dst_fd)
    finally:
        if dst_fd is not None: os.close(dst_fd)
        if src_fd is not None: os.close(src_fd)
    readback=hashlib.sha256();checked=0
    fd=os.open(dst,os.O_RDONLY|os.O_NOFOLLOW|os.O_CLOEXEC)
    try:
        if not stat.S_ISREG(os.fstat(fd).st_mode): raise WriteRejected('Readback is not regular file')
        while True:
            if cancelled and cancelled(): raise WriteCancelled('Cancelled during verification')
            block=os.read(fd,chunk_size)
            if not block:break
            readback.update(block);checked+=len(block)
            if progress:progress('verify',checked,total)
    finally: os.close(fd)
    if checked!=total or readback.digest()!=digest.digest():
        raise WriteRejected('Readback checksum mismatch')
    return {'status':'VERIFIED_REGULAR_FILE_ONLY','bytes':total,'sha256':digest.hexdigest(),
            'physical_usb_writing':False,'write_authorized':False}
