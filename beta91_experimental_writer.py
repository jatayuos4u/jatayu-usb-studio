#!/usr/bin/env python3
"""EXPERIMENTAL standalone writer. Not integrated with GUI or Polkit. DO NOT DEPLOY.

Physical writes are only possible via root and multiple explicit flags. No auto-escalation.
A separate security audit and disposable hardware validation are required.
"""
import argparse
import hashlib
import json
import os
import stat
import signal
from privileged_writer_contract import inspect_live, revalidate

from studio_device_safety import UnsafeTarget, WriteCancelled, reject_active_swap, validate_target, stage_iso_verified

def verify_readback(fd, expected_digest, size, *, chunk=1024*1024, cancelled=lambda: False, progress=None):
    """Verify exact written prefix by reading the *same* already-open device fd."""
    if size <= 0 or chunk <= 0: raise UnsafeTarget("Invalid readback bounds")
    os.lseek(fd, 0, os.SEEK_SET)
    h = hashlib.sha256(); done = 0
    while done < size:
        if cancelled(): raise WriteCancelled("Cancelled during readback")
        block = os.read(fd, min(chunk, size-done))
        if not block: raise UnsafeTarget("Readback truncated")
        h.update(block); done += len(block)
        if progress: progress("verify", done, size)
    if h.hexdigest() != expected_digest: raise UnsafeTarget("Readback SHA-256 mismatch")
    return h.hexdigest()

def assert_open_target_identity(fd, expected):
    """Reject an opened descriptor that no longer matches the inspected disk.

    Recheck the opened descriptor and current kernel sysfs identity; never
    infer device identity from a potentially replaced pathname alone.
    """
    current = os.fstat(fd)
    if not stat.S_ISBLK(current.st_mode):
        raise UnsafeTarget('Opened target is not a block device')
    if (os.major(current.st_rdev), os.minor(current.st_rdev)) != (expected.major, expected.minor):
        raise UnsafeTarget('Opened device major/minor changed')
    if not revalidate(expected):
        raise UnsafeTarget('Target identity changed after open')
    return True

def write_iso(iso, target, *, execute=False, confirm='', inspector=inspect_live,
              validator=validate_target, chunk=1024*1024, cancelled=lambda: False, progress=None):
    identity=inspector(target)
    validator(target,identity)
    if not execute:return {'status':'PREFLIGHT_ONLY','writing_enabled':False,'device':target}
    if os.geteuid()!=0:raise UnsafeTarget('Root required for experimental write')
    if confirm != 'ERASE '+target:raise UnsafeTarget('Exact erase confirmation missing')
    # Stage a private source snapshot BEFORE opening the destructive target.
    # This is a prototype hardening measure, not an authorization mechanism.
    snapshot, source_digest, source_size = stage_iso_verified(
        iso, max_bytes=identity.size_bytes, chunk=chunk, cancelled=cancelled)
    dst=None
    try:
        validator(target,identity)
        dst=os.open(target,os.O_RDWR|os.O_EXCL|os.O_NOFOLLOW|os.O_CLOEXEC|os.O_SYNC)
        dt=os.fstat(dst)
        if not stat.S_ISBLK(dt.st_mode) or (os.major(dt.st_rdev),os.minor(dt.st_rdev))!=(identity.major,identity.minor):
            raise UnsafeTarget('Opened device does not match inspected target')
        validator(target,identity)
        # Bind the preflight to the opened descriptor, not just a pathname.
        # This is defense-in-depth; it is NOT a replacement for a Polkit service.
        assert_open_target_identity(dst, identity)
        written=0
        while written<source_size:
            if cancelled(): raise WriteCancelled('Cancelled during write; target may be partially overwritten')
            buf=snapshot.read(min(chunk,source_size-written))
            if not buf:raise UnsafeTarget('Staged source truncated')
            view=memoryview(buf)
            while view:
                n=os.write(dst,view)
                if n<=0:raise UnsafeTarget('Short block-device write')
                view=view[n:]
            written+=len(buf)
            if progress: progress('write',written,source_size)
            else: print(json.dumps({'phase':'write','bytes':written,'total':source_size}),flush=True)
        os.fsync(dst)
        verified_digest = verify_readback(dst,source_digest,source_size,
                                          chunk=chunk,cancelled=cancelled,progress=progress)
    finally:
        if dst is not None:os.close(dst)
        snapshot.close()
    # This remains an unsafe prototype without a privileged Polkit service,
    # fd-bound mount topology enforcement, or hardware validation.
    return {'status':'EXPERIMENTAL_WRITTEN_VERIFIED','bytes':written,
            'sha256_source':source_digest,'sha256_readback':verified_digest,'physical_usb_writing':True}

def main():
    p=argparse.ArgumentParser(description='Experimental destructive writer; NOT for deployment')
    p.add_argument('--iso',required=True);p.add_argument('--device',required=True)
    p.add_argument('--execute',action='store_true');p.add_argument('--confirm',default='')
    args=p.parse_args()
    try:print(json.dumps(write_iso(args.iso,args.device,execute=args.execute,confirm=args.confirm)))
    except (UnsafeTarget,OSError,ValueError) as e:p.error(str(e))
if __name__=='__main__':main()
