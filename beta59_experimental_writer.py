#!/usr/bin/env python3
"""Beta 59 experimental physical USB writer. NOT integrated with GUI or Polkit.

Runs as root only with an explicit opt-in; defaults to read-only preflight.
No shell commands are executed. Do not use on a drive containing valuable data.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import stat
import sys
import time
import fcntl
from iso_write_preflight import inspect_iso

BLOCK = Path('/sys/class/block')
CHUNK = 1024 * 1024

class Refused(Exception): pass

def sysvalue(path):
    return Path(path).read_text().strip()

def mounts_and_swaps():
    paths=set()
    for fn in ('/proc/self/mountinfo','/proc/swaps'):
        with open(fn,encoding='utf-8') as f:
            for line in f:
                if fn.endswith('mountinfo'):
                    fields=line.split(); dev=fields[2]; paths.add(dev)
                else:
                    if line.startswith('Filename'): continue
                    p=line.split()[0]
                    try:
                        s=os.stat(p)
                        if stat.S_ISBLK(s.st_mode):
                            paths.add(f'{os.major(s.st_rdev)}:{os.minor(s.st_rdev)}')
                    except OSError: pass
    return paths

def device_info(device):
    if not device.startswith('/dev/') or Path(device).name != device[5:] or '/' in device[5:]:
        raise Refused('Expected a direct /dev block disk path')
    node=BLOCK / device[5:]
    if not node.exists() or (node/'partition').exists(): raise Refused('Not a whole block disk')
    fd=os.open(device,os.O_RDONLY|os.O_CLOEXEC|os.O_NONBLOCK|os.O_NOFOLLOW)
    try:
        st=os.fstat(fd)
        if not stat.S_ISBLK(st.st_mode): raise Refused('Not a block device')
        devnum=f'{os.major(st.st_rdev)}:{os.minor(st.st_rdev)}'
        if sysvalue(node/'dev') != devnum: raise Refused('sysfs device identity mismatch')
        real=(node/'device').resolve()
        if '/usb' not in str(real).lower(): raise Refused('Not on a USB bus')
        if sysvalue(node/'removable')!='1' or sysvalue(node/'ro')!='0':
            raise Refused('Not removable and writable')
        size=int(sysvalue(node/'size'))*512
        if size<1024*1024 or size>128*1024**3: raise Refused('Device size outside test range')
        children=[]
        for n in BLOCK.iterdir():
            if (n/'partition').exists() and n.resolve().parent==node.resolve():
                children.append(n)
        active=mounts_and_swaps()
        for n in [node]+children:
            if sysvalue(n/'dev') in active: raise Refused('Disk or partition is mounted or swap')
            holders=n/'holders'
            if holders.exists() and any(holders.iterdir()): raise Refused('Device has holders')
        # The physical path is used as a second identity marker alongside major:minor.
        return {'path':device,'devnum':devnum,'sysfs':str(real),'bytes':size,'children':[n.name for n in children]}
    finally: os.close(fd)

def write_test(iso, device, expected_sha, confirm, *, allow_write=False):
    report=inspect_iso(iso)
    if not report['ok']: raise Refused(report.get('reason','Invalid ISO'))
    if report['sha256']!=expected_sha: raise Refused('ISO SHA-256 mismatch')
    info=device_info(device)
    if report['iso_size_bytes']>info['bytes']: raise Refused('ISO larger than USB')
    if not allow_write:
        return {'mode':'read-only','iso_sha256':expected_sha,'iso_bytes':report['iso_size_bytes'], 'device':info,'writing_enabled':False}
    if os.geteuid()!=0: raise Refused('Writing requires root; Polkit integration is not implemented')
    if confirm!=f'ERASE {device}': raise Refused('Confirmation must exactly match ERASE /dev/DEVICE')
    flags=os.O_RDWR|os.O_EXCL|os.O_CLOEXEC|os.O_NOFOLLOW|os.O_SYNC
    if hasattr(os,'O_NONBLOCK'): flags|=os.O_NONBLOCK
    # Exclusive open denies concurrently claimed devices. Recheck metadata while held.
    dfd=os.open(device,flags)
    try:
        st=os.fstat(dfd)
        if not stat.S_ISBLK(st.st_mode) or f'{os.major(st.st_rdev)}:{os.minor(st.st_rdev)}'!=info['devnum']:
            raise Refused('Device changed before write')
        if device_info(device)!=info: raise Refused('USB identity/topology changed before write')
        if not sys.stdin.isatty(): raise Refused('Interactive terminal required')
        print(f'FINAL WARNING: This permanently erases {device}, {info["bytes"]} bytes, {info["sysfs"]}',file=sys.stderr)
        answer=input('Type the exact device path to proceed: ')
        if answer!=device: raise Refused('Final confirmation declined')
        sfd=os.open(iso,os.O_RDONLY|os.O_NOFOLLOW|os.O_CLOEXEC)
        try:
            before=os.fstat(sfd)
            if not stat.S_ISREG(before.st_mode) or before.st_size!=report['iso_size_bytes']:
                raise Refused('ISO changed')
            # Rehash the same open file descriptor before first write.
            h=hashlib.sha256()
            while True:
                buf=os.read(sfd,CHUNK)
                if not buf: break
                h.update(buf)
            if h.hexdigest()!=expected_sha: raise Refused('ISO changed before write')
            os.lseek(sfd,0,os.SEEK_SET)
            written=0
            while True:
                buf=os.read(sfd,CHUNK)
                if not buf: break
                view=memoryview(buf)
                while view:
                    count=os.write(dfd,view)
                    if count<=0: raise OSError('Short write')
                    written+=count
                    view=view[count:]
                print(f'Written {written}/{before.st_size} bytes',file=sys.stderr)
            os.fsync(dfd)
            after=os.fstat(sfd)
            if (before.st_dev,before.st_ino,before.st_size,before.st_mtime_ns)!=(after.st_dev,after.st_ino,after.st_size,after.st_mtime_ns):
                raise Refused('ISO changed during writing; USB contents may be incomplete')
            os.lseek(dfd,0,os.SEEK_SET)
            verify=hashlib.sha256(); remaining=written
            while remaining:
                chunk=os.read(dfd,min(CHUNK,remaining))
                if not chunk: raise Refused('Unexpected EOF during verification')
                verify.update(chunk); remaining-=len(chunk)
            if verify.hexdigest()!=expected_sha: raise Refused('USB read-back verification failed')
            return {'mode':'written-and-verified','bytes':written,'sha256':expected_sha,'device':device}
        finally: os.close(sfd)
    finally: os.close(dfd)

def main():
    p=argparse.ArgumentParser(description='EXPERIMENTAL physical writer. Default is read-only.')
    p.add_argument('--iso',required=True); p.add_argument('--device',required=True)
    p.add_argument('--sha256',help='Expected full ISO SHA-256 (required for writing)')
    p.add_argument('--experimental-write',action='store_true')
    p.add_argument('--confirm',default='')
    args=p.parse_args()
    try:
        iso_report=inspect_iso(args.iso)
        if not iso_report['ok']: raise Refused(iso_report['reason'])
        if args.sha256 and args.sha256!=iso_report['sha256']: raise Refused('ISO hash mismatch')
        result=write_test(args.iso,args.device,args.sha256 or iso_report['sha256'],args.confirm,allow_write=args.experimental_write)
        print(json.dumps({'ok':True,**result},indent=2)); return 0
    except (Refused,OSError,ValueError) as e:
        print(json.dumps({'ok':False,'reason':str(e)}),file=sys.stderr); return 1
if __name__=='__main__': raise SystemExit(main())
