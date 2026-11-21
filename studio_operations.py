"""Unprivileged USB Studio operations and JSON-lines GUI protocol."""
import argparse
import array
from contextlib import contextmanager
import ctypes
import errno
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import select
import signal
import ssl
import stat
import struct
import subprocess
import sys
import tempfile
import time
import urllib.parse
import urllib.request

from privileged_writer_contract import inspect_live
from studio_device_safety import UnsafeTarget, WriteCancelled, stage_iso_verified, validate_target, snapshot_locations, snapshot_space_error
from udisks2_backend import inspect_usb, object_path
from verified_write_transaction import transfer_and_verify

CHUNK = 1024 * 1024
MAX_ISO_DOWNLOAD_BYTES = 16 * 1024**3
ISO_DOWNLOAD_SECONDS = 2 * 60 * 60
BLKGETSIZE64 = 0x80081272  # Linux AMD64 _IOR(0x12, 114, size_t)
BLKGETDISKSEQ = 0x80081280  # Linux AMD64 _IOR(0x12, 128, __u64)
SERVICE = 'org.freedesktop.UDisks2'
BLOCK = SERVICE + '.Block'


def check_cancel(cancelled):
    if cancelled():
        raise WriteCancelled('Operation cancelled')


def disk_sequence(device):
    object_path(device)
    sequence = int((Path('/sys/class/block') / Path(device).name / 'diskseq').read_text())
    if sequence <= 0:
        raise UnsafeTarget('Kernel disk generation unavailable')
    return sequence


def inspect_selection(device, sequence):
    if disk_sequence(device) != sequence:
        raise UnsafeTarget('Selected drive was replaced. Refresh and select it again.')
    identity = inspect_live(device)
    validate_target(device, identity)
    node = Path(identity.sysfs_path)
    if not (node / 'holders').is_dir() or any(
            not (child / 'holders').is_dir() for child in node.iterdir() if (child / 'partition').is_file()):
        raise UnsafeTarget('Kernel holder information is incomplete')
    topology = inspect_usb(device)
    if topology['size_bytes'] != identity.size_bytes or disk_sequence(device) != sequence:
        raise UnsafeTarget('Selected drive changed during inspection')
    return identity


def attest_fd(fd, identity, sequence, *, writable):
    current = os.fstat(fd)
    actual_access = fcntl.fcntl(fd, fcntl.F_GETFL) & os.O_ACCMODE
    if not stat.S_ISBLK(current.st_mode) or (os.major(current.st_rdev), os.minor(current.st_rdev)) != (identity.major, identity.minor):
        raise UnsafeTarget('UDisks2 returned a descriptor for a different device')
    if actual_access != (os.O_RDWR if writable else os.O_RDONLY):
        raise UnsafeTarget('UDisks2 returned an unexpected descriptor access mode')
    capacity = array.array('Q', [0])
    fcntl.ioctl(fd, BLKGETSIZE64, capacity, True)
    if capacity[0] != identity.size_bytes:
        raise UnsafeTarget('Opened device capacity changed')
    require_fd_generation(fd, sequence)
    if disk_sequence(identity.path) != sequence:
        raise UnsafeTarget('Opened USB drive no longer matches the confirmed disk generation')
    return True


def require_fd_generation(fd, sequence):
    generation = array.array('Q', [0])
    fcntl.ioctl(fd, BLKGETDISKSEQ, generation, True)
    if generation[0] != sequence:
        raise UnsafeTarget('USB medium changed during the operation')


@contextmanager
def open_usb(device, sequence, identity, *, writable, cancelled):
    import gi
    gi.require_version('Gio', '2.0')
    from gi.repository import Gio, GLib

    check_cancel(cancelled)
    bus = Gio.bus_get_sync(Gio.BusType.SYSTEM, None)
    if inspect_selection(device, sequence) != identity:
        raise UnsafeTarget('Selected drive changed before authorization')
    # O_EXCL claims the disk against mounting, swap activation and another
    # cooperating exclusive user, even while the GUI waits for authentication.
    options = {'flags': GLib.Variant('i', os.O_EXCL | os.O_NOFOLLOW)}
    params = GLib.Variant('(sa{sv})', ('rw' if writable else 'r', options))
    reply, descriptors = bus.call_with_unix_fd_list_sync(
        SERVICE, object_path(device), BLOCK, 'OpenDevice', params,
        GLib.VariantType.new('(h)'), Gio.DBusCallFlags.ALLOW_INTERACTIVE_AUTHORIZATION, 120000, None, None)
    if descriptors is None:
        raise UnsafeTarget('UDisks2 returned no device descriptor')
    handle = reply.unpack()[0]
    if not 0 <= handle < descriptors.get_length():
        raise UnsafeTarget('Invalid UDisks2 descriptor index')
    fd = descriptors.get(handle)
    del descriptors
    try:
        attest_fd(fd, identity, sequence, writable=writable)
        if inspect_selection(device, sequence) != identity:
            raise UnsafeTarget('Selected drive changed during authorization')
        check_cancel(cancelled)
        yield fd
    finally:
        os.close(fd)


def hash_prefix(fd, size, progress, cancelled, sequence):
    digest = hashlib.sha256()
    done = 0
    while done < size:
        check_cancel(cancelled)
        require_fd_generation(fd, sequence)
        block = os.read(fd, min(CHUNK, size - done))
        if not block:
            raise UnsafeTarget('USB readback ended before the full image was read')
        digest.update(block)
        done += len(block)
        progress('verify', done, size)
    return digest.hexdigest()


def require_iso(snapshot, size):
    # ISO 9660 volume descriptor signature, used by Linux hybrid ISOs.
    for sector in range(16, min(64, size // 2048)):
        descriptor = os.pread(snapshot.fileno(), 2048, sector * 2048)
        if descriptor[:7] != b'\x01CD001\x01':
            continue
        little_volume, = struct.unpack_from('<I', descriptor, 80)
        big_volume, = struct.unpack_from('>I', descriptor, 84)
        little_block, = struct.unpack_from('<H', descriptor, 128)
        big_block, = struct.unpack_from('>H', descriptor, 130)
        if (little_volume != big_volume or little_block != big_block or little_block != 2048
                or little_volume <= sector or little_volume * little_block > size):
            raise UnsafeTarget('ISO volume dimensions are invalid or the image is truncated')
        return descriptor
    raise UnsafeTarget('A primary ISO 9660 volume descriptor was not found. Raw USB writing requires a hybrid Linux ISO, and standard Windows installer ISOs use the separate Windows mode.')


def iso_directory_entries(fd, extent, length, image_size):
    """Read a bounded ISO 9660 directory from the staged snapshot."""
    offset = extent * 2048
    if not 0 < length <= 1024 * 1024 or offset + length > image_size:
        return
    data = os.pread(fd, length, offset)
    cursor = 0
    while cursor < len(data):
        record_length = data[cursor]
        if not record_length:
            cursor = (cursor // 2048 + 1) * 2048
            continue
        record = data[cursor:cursor + record_length]
        cursor += record_length
        if len(record) < 34 or 33 + record[32] > len(record):
            return
        yield record[33:33 + record[32]].split(b';', 1)[0].upper(), record


def looks_like_windows_installer(snapshot, descriptor, size):
    identifiers = b' '.join((descriptor[8:40], descriptor[318:446], descriptor[574:702])).upper()
    if any(marker in identifiers for marker in (b'MICROSOFT', b'CDIMAGE', b'OSCDIMG')):
        return True
    root_extent = struct.unpack_from('<I', descriptor, 158)[0]
    root_length = struct.unpack_from('<I', descriptor, 166)[0]
    for name, record in iso_directory_entries(snapshot.fileno(), root_extent, root_length, size):
        if name == b'SOURCES' and record[25] & 2:
            extent = struct.unpack_from('<I', record, 2)[0]
            length = struct.unpack_from('<I', record, 10)[0]
            names = {name for name, _ in iso_directory_entries(snapshot.fileno(), extent, length, size)}
            return b'BOOT.WIM' in names and bool(names & {b'INSTALL.WIM', b'INSTALL.ESD', b'INSTALL.SWM'})
    return False


def require_linux_write_image(image, size):
    descriptor = require_iso(image, size)
    if looks_like_windows_installer(image, descriptor, size):
        raise UnsafeTarget('This appears to be a Windows installer ISO. Choose Create Windows installer (UEFI). No data was written to the target USB.')


def disk_operation(args, progress, cancelled, *, confirm_write=lambda: None):
    identity = inspect_selection(args.device, args.sequence)
    if args.operation == 'clone':
        source = inspect_selection(args.source, args.source_sequence)
        if (source.major, source.minor) == (identity.major, identity.minor) or source.size_bytes > identity.size_bytes:
            raise UnsafeTarget('Clone needs two distinct disks and enough destination capacity')
        with open_usb(args.source, args.source_sequence, source, writable=False, cancelled=cancelled) as fd:
            return write_image(fd, source.size_bytes, args, identity, progress, cancelled, confirm_write,
                               source_liveness=lambda: require_fd_generation(fd, args.source_sequence))
    if args.operation == 'windows':
        sector_file = Path(identity.sysfs_path) / 'queue/logical_block_size'
        if int(sector_file.read_text()) != 512:
            raise UnsafeTarget('Windows installer mode requires a USB with 512-byte logical sectors.')
        progress('Checking Windows workspace', 0, 0)
    if args.operation == 'write':
        progress('Checking image compatibility', 0, 0)

    def stage_progress(done, total):
        progress('Staging ISO', done, total)

    snapshot, digest, size = stage_iso_verified(
        args.iso, max_bytes=identity.size_bytes, cancelled=cancelled,
        progress=stage_progress,
        preflight=require_linux_write_image if args.operation == 'write' else None)
    with snapshot:
        if args.operation == 'windows':
            from windows_installer import prepare_windows_image, WORKSPACE_MARGIN
            progress('Checking Windows workspace', 0, 0)
            # Allow for extracted files, the FAT image, and temporary WIM parts.
            with filesystem_workspace(3 * size + 2 * WORKSPACE_MARGIN) as work:
                image, image_size = prepare_windows_image(
                    snapshot, size, Path(work), identity.size_bytes, progress, cancelled)
                with image.open('rb') as media:
                    return write_image(media.fileno(), image_size, args, identity,
                                       progress, cancelled, confirm_write)
        if args.operation == 'write':
            require_linux_write_image(snapshot, size)
        else:
            require_iso(snapshot, size)
        if args.operation == 'verify':
            with open_usb(args.device, args.sequence, identity, writable=False, cancelled=cancelled) as fd:
                actual = hash_prefix(fd, size, progress, cancelled, args.sequence)
                attest_fd(fd, identity, args.sequence, writable=False)
                if actual != digest:
                    raise UnsafeTarget('SHA-256 mismatch between the ISO and the USB image prefix')
                return {'status': 'IMAGE_MATCH', 'sha256': digest, 'bytes': size}
        result = write_image(snapshot.fileno(), size, args, identity, progress, cancelled, confirm_write)
        if result['sha256'] != digest:
            raise UnsafeTarget('Staged ISO checksum mismatch')
        return result


def write_image(source_fd, size, args, identity, progress, cancelled, confirm_write, *, source_liveness=None):
    progress('Waiting for UDisks2 authorization', 0, 0)
    with open_usb(args.device, args.sequence, identity, writable=True, cancelled=cancelled) as fd:
        confirm_write()

        def liveness():
            require_fd_generation(fd, args.sequence)
            if source_liveness is not None:
                source_liveness()

        if args.operation == 'windows' and identity.size_bytes > size:
            # Remove a previous GPT backup at the end of the USB. Otherwise
            # partition scanners may prefer it to the newly written MBR.
            tail = min(identity.size_bytes - size, 33 * 512)
            with tempfile.TemporaryFile() as zeros:
                zeros.truncate(tail)
                transfer_and_verify(
                    zeros.fileno(), fd, tail, target_offset=identity.size_bytes - tail,
                    progress=lambda phase, done, total: progress(
                        'Clearing old partition metadata' if phase == 'write' else
                        'Verifying cleared partition metadata', done, total),
                    cancelled=cancelled,
                    pre_write_check=lambda opened: attest_fd(opened, identity, args.sequence, writable=True),
                    liveness_check=liveness)
        result = transfer_and_verify(
            source_fd, fd, size, progress=progress, cancelled=cancelled,
            pre_write_check=lambda opened: attest_fd(opened, identity, args.sequence, writable=True),
            liveness_check=liveness)
        liveness()
        attest_fd(fd, identity, args.sequence, writable=True)
        return result



FILESYSTEMS = {
    'vfat': ('/usr/sbin/mkfs.fat', ['-F', '32'], '/usr/sbin/fsck.fat', ['-n'], ['-a']),
    'exfat': ('/usr/sbin/mkfs.exfat', [], '/usr/sbin/fsck.exfat', ['-n'], ['-p']),
    'ntfs': ('/usr/sbin/mkfs.ntfs', ['-F', '-Q', '-s', '512'], '/usr/sbin/ntfsresize',
             ['--info', '--no-progress-bar'], None),
    'ext4': ('/usr/sbin/mkfs.ext4', ['-F'], '/usr/sbin/e2fsck', ['-f', '-n'], ['-f', '-p']),
}


def run_fs_tool(program, arguments, path, cancelled):
    with tempfile.TemporaryFile() as log:
        with subprocess.Popen([program, *arguments, str(path)], stdout=log,
                              stderr=subprocess.STDOUT, env={**os.environ, 'LC_ALL': 'C'}) as process:
            while True:
                try:
                    status = process.wait(timeout=0.25)
                    break
                except subprocess.TimeoutExpired:
                    if cancelled():
                        process.kill()
                        process.wait()
                        raise WriteCancelled('Filesystem tool cancelled on its private snapshot')
        log.seek(max(0, log.tell() - 8192))
        return status, log.read().decode(errors='replace').strip()


def filesystem_extent(identity, partition):
    if not partition or partition == identity.path:
        return 0, identity.size_bytes
    name = Path(partition).name
    node = Path(identity.sysfs_path) / name
    if partition != f'/dev/{name}' or not re.fullmatch(r'[a-z]+[a-z0-9]*[0-9]', name):
        raise UnsafeTarget('Invalid filesystem partition selection')
    if not (node / 'partition').is_file():
        raise UnsafeTarget('Selected partition does not belong to the approved USB disk')
    start = int((node / 'start').read_text()) * 512
    length = int((node / 'size').read_text()) * 512
    if start <= 0 or length <= 0 or start + length > identity.size_bytes:
        raise UnsafeTarget('Partition extent is outside the selected USB disk')
    return start, length


def verify_fat_filesystem(fd):
    """Probe the authorized descriptor without reopening the device node."""
    blkid = ctypes.CDLL('libblkid.so.1')
    pointer = ctypes.c_void_p
    signatures = (
        ('blkid_new_probe', [], pointer),
        ('blkid_free_probe', [pointer], None),
        ('blkid_probe_set_device', [pointer, ctypes.c_int, ctypes.c_int64, ctypes.c_int64], ctypes.c_int),
        ('blkid_do_safeprobe', [pointer], ctypes.c_int),
        ('blkid_probe_lookup_value', [pointer, ctypes.c_char_p, ctypes.POINTER(ctypes.c_char_p),
                                     ctypes.POINTER(ctypes.c_size_t)], ctypes.c_int),
    )
    for name, arguments, result in signatures:
        function = getattr(blkid, name)
        function.argtypes = arguments
        function.restype = result

    probe = blkid.blkid_new_probe()
    if not probe:
        raise UnsafeTarget('Unable to allocate the filesystem probe')
    try:
        if blkid.blkid_probe_set_device(probe, fd, 0, 0) != 0:
            raise UnsafeTarget('Filesystem probe could not attach to the authorized USB handle')
        status = blkid.blkid_do_safeprobe(probe)
        if status == -2:
            raise UnsafeTarget('Conflicting filesystem signatures remain. Full format can clear them.')
        if status < 0:
            raise UnsafeTarget('Filesystem probe failed while reading the authorized USB handle')
        filesystem = ctypes.c_char_p()
        if status or blkid.blkid_probe_lookup_value(probe, b'TYPE', ctypes.byref(filesystem), None) or filesystem.value != b'vfat':
            raise UnsafeTarget('FAT filesystem was not detected after quick format')
    finally:
        blkid.blkid_free_probe(probe)


def fat32_format_ranges(fd, size):
    """Cover FAT32 metadata and old signatures at both disk boundaries."""
    boot = os.pread(fd, 512, 0)
    if len(boot) != 512 or boot[510:] != b'\x55\xaa':
        raise UnsafeTarget('Invalid FAT32 boot sector')
    sector, cluster, reserved, fats = struct.unpack_from('<HBHB', boot, 11)
    fat_sectors = struct.unpack_from('<I', boot, 36)[0]
    root = struct.unpack_from('<I', boot, 44)[0]
    metadata = (reserved + fats * fat_sectors + cluster) * sector
    if sector != 512 or not cluster or not reserved or not fats or not fat_sectors or root != 2 or metadata > size:
        raise UnsafeTarget('Unexpected FAT32 filesystem layout')
    boundary = 4 * 1024 * 1024
    prefix = max(boundary, metadata)
    if prefix >= size - boundary:
        return [(0, size)]
    return [(0, prefix), (size - boundary, boundary)]


def check_filesystem(args, progress, cancelled):
    """Ask UDisks2 for a read-only check without staging a disk image."""
    import gi
    gi.require_version('Gio', '2.0')
    from gi.repository import Gio, GLib

    check_cancel(cancelled)
    identity = inspect_selection(args.device, args.sequence)
    extent = filesystem_extent(identity, args.partition)
    path = (object_path(args.device).rsplit('/', 1)[0] + '/' +
            Path(args.partition or args.device).name)
    bus = Gio.bus_get_sync(Gio.BusType.SYSTEM, None)
    progress('Checking filesystem through UDisks2', 0, 0)
    try:
        reply = bus.call_sync(
            SERVICE, path, SERVICE + '.Filesystem', 'Check',
            GLib.Variant('(a{sv})', ({},)), GLib.VariantType.new('(b)'),
            Gio.DBusCallFlags.ALLOW_INTERACTIVE_AUTHORIZATION, 300000, None)
    except GLib.Error as exc:
        remote = Gio.DBusError.get_remote_error(exc)
        if remote in ('org.freedesktop.UDisks2.Error.NotSupported',
                      'org.freedesktop.DBus.Error.UnknownMethod',
                      'org.freedesktop.DBus.Error.UnknownInterface'):
            check_cancel(cancelled)
            return filesystem_operation(args, progress, cancelled)
        raise UnsafeTarget(f'UDisks2 filesystem check could not complete: {exc.message}') from exc
    check_cancel(cancelled)
    if inspect_selection(args.device, args.sequence) != identity or filesystem_extent(identity, args.partition) != extent:
        raise UnsafeTarget('USB selection changed during the filesystem check')
    consistent, = reply.unpack()
    return {'status': 'FILESYSTEM_CLEAN' if consistent else 'FILESYSTEM_FINDINGS',
            'message': 'UDisks2 completed a read-only consistency check.'}


def filesystem_workspace(size):
    for directory in snapshot_locations(size):
        try:
            return tempfile.TemporaryDirectory(prefix='jatayu-usb-', dir=directory)
        except OSError:
            continue
    raise snapshot_space_error(size, 'USB filesystem snapshot')


def filesystem_operation(args, progress, cancelled, *, confirm_write=lambda: None):
    identity = inspect_selection(args.device, args.sequence)
    formatting = args.operation == 'format'
    quick = formatting and args.filesystem == 'vfat' and not getattr(args, 'full_format', False)
    writing = args.operation != 'check'
    before = filesystem_extent(identity, args.partition)
    start, size = (0, identity.size_bytes) if formatting else before
    if not formatting:
        progress('Preparing filesystem snapshot', 0, 0)
    workspace = tempfile.TemporaryDirectory(prefix='jatayu-usb-') if formatting else filesystem_workspace(size)
    with workspace as folder:
        image = Path(folder) / 'filesystem.img'
        with image.open('xb') as output:
            os.fchmod(output.fileno(), 0o600)
            output.truncate(size)
        if formatting:
            mkfs, flags, checker, check_flags, _ = FILESYSTEMS[args.filesystem]
            logical_sector = int((Path(identity.sysfs_path) / 'queue/logical_block_size').read_text())
            if logical_sector != 512:
                raise UnsafeTarget('Formatting currently requires a 512-byte logical sector device')
            progress('Building filesystem image', 0, 0)
            status, report = run_fs_tool(mkfs, flags, image, cancelled)
            if status:
                raise UnsafeTarget(report or 'Filesystem creation failed')
            status, report = run_fs_tool(checker, check_flags, image, cancelled)
            if status:
                raise UnsafeTarget(report or 'New filesystem failed its consistency check')
        progress('Waiting for UDisks2 authorization', 0, 0)
        with open_usb(args.device, args.sequence, identity, writable=writing, cancelled=cancelled) as fd:
            if not formatting:
                if filesystem_extent(identity, args.partition) != before:
                    raise UnsafeTarget('Partition layout changed during authorization')
                try:
                    with image.open('r+b') as output:
                        done = 0
                        while done < size:
                            check_cancel(cancelled)
                            require_fd_generation(fd, args.sequence)
                            block = os.pread(fd, min(CHUNK, size - done), start + done)
                            if not block:
                                raise UnsafeTarget('Filesystem snapshot read ended early')
                            output.write(block)
                            done += len(block)
                            progress('Reading filesystem snapshot', done, size)
                except OSError as exc:
                    if exc.errno in (errno.ENOSPC, errno.EDQUOT):
                        raise UnsafeTarget(
                            f'Filesystem snapshot ran out of space or exceeded a quota in {folder}. '
                            f'Free at least {size:,} bytes on that filesystem and retry. '
                            'No data was written to the target USB.') from exc
                    raise
                identified = subprocess.run(['/usr/sbin/blkid', '-p', '-s', 'TYPE', '-o', 'value', str(image)],
                                                capture_output=True, text=True, timeout=15, check=False)
                filesystem = identified.stdout.strip()
                if identified.returncode or filesystem not in FILESYSTEMS:
                    raise UnsafeTarget('Filesystem is ambiguous or unsupported. Supported types are FAT, exFAT, NTFS and ext4.')
                if filesystem == 'ext4':
                    with image.open('rb') as snapshot:
                        snapshot.seek(1024)
                        superblock = snapshot.read(1024)
                    compat = struct.unpack_from('<I', superblock, 0x5c)[0]
                    journal_inode, journal_device = struct.unpack_from('<II', superblock, 0xe0)
                    if journal_device or (compat & 4 and not journal_inode):
                        raise UnsafeTarget('Filesystems with external journals are unsupported')
                _, _, checker, check_flags, repair_flags = FILESYSTEMS[filesystem]
                if writing and repair_flags is None:
                    raise UnsafeTarget('NTFS automatic repair is unavailable. Use Windows chkdsk for NTFS repair.')
                progress(f'Checking {filesystem}', 0, 0)
                status, report = run_fs_tool(checker, check_flags, image, cancelled)
                journal_pending = filesystem == 'ext4' and 'skipping journal recovery' in report.lower()
                if not status and not journal_pending:
                    return {'status': 'FILESYSTEM_CLEAN', 'message': f'{filesystem}: supported checks passed. ' + report}
                if not writing:
                    return {'status': 'FILESYSTEM_FINDINGS', 'message': f'{filesystem}: check exited with status {status}. ' + report}
                if filesystem == 'ext4' and status & ~4:
                    raise UnsafeTarget(report or 'Read-only ext4 check could not complete')
                progress(f'Repairing {filesystem} snapshot', 0, 0)
                status, repair_report = run_fs_tool(checker, repair_flags, image, cancelled)
                if status not in (0, 1):
                    raise UnsafeTarget(repair_report or 'Automatic repair did not complete')
                status, report = run_fs_tool(checker, check_flags, image, cancelled)
                if status or (filesystem == 'ext4' and 'skipping journal recovery' in report.lower()):
                    raise UnsafeTarget(report or 'Repaired snapshot failed its consistency check')
            confirm_write()
            if not formatting and filesystem_extent(identity, args.partition) != before:
                raise UnsafeTarget('Partition layout changed before repair write')
            with image.open('rb') as source:
                ranges = fat32_format_ranges(source.fileno(), size) if quick else [(0, size)]
                total = sum(length for _, length in ranges)
                for index, (offset, length) in enumerate(ranges, 1):
                    def report_progress(phase, done, _length):
                        if quick:
                            progress(f'{phase} FAT32 region {index}/{len(ranges)}', done, length)
                        else:
                            progress(phase, done, total)

                    result = transfer_and_verify(
                        source.fileno(), fd, length, source_offset=offset, target_offset=start + offset,
                        progress=report_progress, cancelled=cancelled,
                        pre_write_check=lambda opened: attest_fd(opened, identity, args.sequence, writable=True),
                        liveness_check=lambda: require_fd_generation(fd, args.sequence))
            attest_fd(fd, identity, args.sequence, writable=True)
            if quick:
                check_cancel(cancelled)
                progress('Checking FAT filesystem signature', 0, 0)
                verify_fat_filesystem(fd)
                attest_fd(fd, identity, args.sequence, writable=True)
                return {'status': 'QUICK_FORMAT_VERIFIED', 'bytes': total,
                        'message': 'FAT32 filesystem structures and disk boundary regions passed SHA-256 readback. Other areas were left untouched.'}
            return {**result, 'message': report}


def https_url(value):
    target = urllib.parse.urlsplit(value)
    if target.scheme != 'https' or not target.hostname or target.username is not None or target.password is not None:
        raise ValueError('Enter an HTTPS URL without embedded credentials')
    return target


class HttpsRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        https_url(newurl)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


@contextmanager
def download_deadline(seconds):
    """Bound the complete CLI transfer, including HTTPS connection and headers."""
    def expired(_number, _frame):
        raise TimeoutError('ISO download exceeded the time limit')

    previous = signal.signal(signal.SIGALRM, expired)
    try:
        signal.setitimer(signal.ITIMER_REAL, seconds)
        yield
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, previous)


def download_iso(url, directory, progress, cancelled, *, opener=None):
    target = https_url(url)
    name = urllib.parse.unquote(target.path.rsplit('/', 1)[-1])
    if not re.fullmatch(r'[^/\\\x00-\x1f\x7f]+\.iso', name, re.IGNORECASE) or name in ('.', '..'):
        raise ValueError('The URL path must end in an ISO filename')
    folder = Path(directory).resolve(strict=True)
    destination = folder / name
    directory_fd = os.open(folder, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        # Keep the writable file private even inside a shared destination.
        pinned_folder = f'/proc/self/fd/{directory_fd}'
        if os.path.lexists(os.path.join(pinned_folder, name)):
            raise FileExistsError('An ISO with this name already exists')
        if opener is None:
            opener = urllib.request.build_opener(
                HttpsRedirect(), urllib.request.HTTPSHandler(context=ssl.create_default_context())).open
        progress('Connecting over HTTPS', 0, 0)
        with tempfile.TemporaryDirectory(dir=pinned_folder) as private, opener(url, timeout=15) as response:
            https_url(response.geturl())
            total = int(response.headers.get('Content-Length', 0))
            if response.status != 200 or total < 0:
                raise ValueError('Server did not return a complete ISO response')
            if total > MAX_ISO_DOWNLOAD_BYTES:
                raise ValueError('ISO download exceeds the 16 GiB limit')
            private_fd = os.open(private, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
            try:
                scratch = os.open('download', os.O_CREAT | os.O_EXCL | os.O_RDWR, 0o600, dir_fd=private_fd)
                with os.fdopen(scratch, 'w+b') as output:
                    digest = hashlib.sha256()
                    done = 0
                    while True:
                        check_cancel(cancelled)
                        block = response.read1(CHUNK)
                        if not block:
                            break
                        if len(block) > MAX_ISO_DOWNLOAD_BYTES - done:
                            raise ValueError('ISO download exceeds the 16 GiB limit')
                        output.write(block)
                        digest.update(block)
                        done += len(block)
                        progress('Downloading', done, total)
                    if done <= 0 or (total and done != total):
                        raise ValueError('Download is empty or truncated')
                    output.flush()
                    os.fsync(output.fileno())
                    require_iso(output, done)
                check_cancel(cancelled)
                if not os.path.samestat(os.stat(folder), os.fstat(directory_fd)):
                    raise UnsafeTarget('Download destination directory changed')
                os.link('download', name, src_dir_fd=private_fd, dst_dir_fd=directory_fd, follow_symlinks=False)
            finally:
                os.close(private_fd)
        return {'status': 'DOWNLOADED', 'path': str(destination), 'sha256': digest.hexdigest(), 'bytes': done}
    finally:
        os.close(directory_fd)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('operation', choices=('write', 'windows', 'clone', 'verify', 'download', 'format', 'check', 'repair', 'inspect'))
    parser.add_argument('--cancel-file', type=Path, required=True)
    parser.add_argument('--device')
    parser.add_argument('--sequence', type=int)
    parser.add_argument('--source')
    parser.add_argument('--partition')
    parser.add_argument('--filesystem', choices=FILESYSTEMS)
    parser.add_argument('--full-format', action='store_true')
    parser.add_argument('--source-sequence', type=int)
    parser.add_argument('--iso')
    parser.add_argument('--url')
    parser.add_argument('--directory')
    parser.add_argument('--confirm')
    args = parser.parse_args()

    def emit(event, **fields):
        print(json.dumps({'event': event, **fields}), flush=True)

    start = phase_start = last_report = time.monotonic()
    current_phase = None

    def progress(phase, done, total):
        nonlocal current_phase, phase_start, last_report
        now = time.monotonic()
        if phase != current_phase:
            phase_start = now
            current_phase = phase
        elif now - last_report < 0.2 and done != total:
            return
        last_report = now
        speed = done / max(now - phase_start, 0.001)
        emit('progress', phase=phase, bytes=done, total=total, elapsed=now - start,
             speed=speed, remaining=max(total - done, 0) / speed if total and speed else None)

    def confirm_write():
        emit('confirm_write', device=args.device, operation=args.operation)
        deadline = time.monotonic() + 120
        while time.monotonic() < deadline:
            check_cancel(cancelled)
            ready, _, _ = select.select([sys.stdin], [], [], 0.25)
            if ready:
                if sys.stdin.readline() == 'WRITE\n':
                    check_cancel(cancelled)
                    return
                break
        raise WriteCancelled('Final write confirmation was declined or expired')

    try:
        os.environ['PATH'] = '/usr/sbin:/usr/bin'
        if os.geteuid() == 0:
            raise UnsafeTarget('Run USB Studio as an ordinary user')
        if args.operation in ('write', 'windows', 'clone', 'format', 'repair') and args.confirm != f'ERASE {args.device}':
            raise UnsafeTarget('Exact destination confirmation required')
        cancelled = args.cancel_file.is_file
        check_cancel(cancelled)
        if args.operation == 'download':
            with download_deadline(ISO_DOWNLOAD_SECONDS):
                result = download_iso(args.url, args.directory, progress, cancelled)
        elif args.operation == 'inspect':
            identity = inspect_selection(args.device, args.sequence)
            result = {'status': 'SAFETY_CHECKED',
                      'message': f'{identity.path} · {identity.size_bytes} bytes · disk generation {args.sequence}. '
                                 'Removable USB identity confirmed. No mounts, holders, active swap or read-only flag detected.'}
        elif args.operation == 'check':
            result = check_filesystem(args, progress, cancelled)
        elif args.operation in ('format', 'repair'):
            result = filesystem_operation(args, progress, cancelled, confirm_write=confirm_write)
        else:
            result = disk_operation(args, progress, cancelled, confirm_write=confirm_write)
        emit('result', **result)
    except WriteCancelled as exc:
        emit('error', message=str(exc))
        emit('result', status='CANCELLED')
        return 1
    except Exception as exc:
        emit('error', message=str(exc))
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
