"""Prepare x64 UEFI Windows media in a private image, with no device access."""
from contextlib import contextmanager
import os
from pathlib import Path
import re
import struct
import subprocess
import tempfile

from studio_device_safety import UnsafeTarget, WriteCancelled

MIB = 1024 * 1024
PARTITION_OFFSET = MIB
FAT_LIMIT = 2**32 - 1
WORKSPACE_MARGIN = 272 * MIB


def check_cancel(cancelled):
    if cancelled():
        raise WriteCancelled('Windows media preparation cancelled. No USB data was written.')


def run_tool(arguments, cancelled):
    check_cancel(cancelled)
    environment = {'PATH': '/usr/sbin:/usr/bin', 'LC_ALL': 'C.UTF-8',
                   'HOME': '/nonexistent',
                   'MTOOLSRC': '/dev/null'}
    with tempfile.TemporaryFile() as log:
        with subprocess.Popen(arguments, stdout=log, stderr=subprocess.STDOUT,
                              env=environment, cwd='/') as process:
            while True:
                try:
                    status = process.wait(timeout=0.25)
                    break
                except subprocess.TimeoutExpired:
                    if cancelled():
                        process.kill()
                        process.wait()
                        check_cancel(cancelled)
        check_cancel(cancelled)
        if status:
            log.seek(max(0, log.tell() - 2048))
            detail = log.read().decode(errors='replace').strip()
            raise UnsafeTarget(f'{Path(arguments[0]).name} could not prepare Windows media. {detail}')


def safe_name(name):
    if (not name or len(name.encode('utf-16-le')) > 510 or name.endswith((' ', '.'))
            or re.search(r'[\x00-\x1f<>:"/\\|?*]', name)
            or re.fullmatch(r'(CON|PRN|AUX|NUL|COM[1-9¹²³]|LPT[1-9¹²³])',
                            name.split('.')[0].rstrip(), re.IGNORECASE)):
        raise UnsafeTarget('The ISO contains a name that cannot be copied safely to FAT32.')


def installer_files(walk, size_of, iso_size, cancelled):
    entries = {}
    allocated = 0
    for root, directories, files in walk():
        check_cancel(cancelled)
        for name in [*directories, *files]:
            safe_name(name)
            path = root.rstrip('/') + '/' + name
            key = path.casefold()
            if key in entries:
                raise UnsafeTarget('The ISO contains conflicting FAT32 paths.')
            size = None
            if name in files:
                size = size_of(path)
                allocated += size
                if size < 0 or allocated > iso_size or (size > FAT_LIMIT and key != '/sources/install.wim'):
                    raise UnsafeTarget('The ISO has an invalid payload size or a file too large for FAT32.')
            entries[key] = (path, size)
            if len(entries) > 100000:
                raise UnsafeTarget('The Windows installer ISO has too many files.')
    required = ('/efi/boot/bootx64.efi', '/sources/boot.wim')
    payloads = ('/sources/install.wim', '/sources/install.esd', '/sources/install.swm')
    if not all(entries.get(key, (None, None))[1] for key in required) or not any(
            entries.get(key, (None, None))[1] for key in payloads):
        raise UnsafeTarget('This ISO is missing the x64 UEFI boot loader or Windows Setup files.')
    return entries


class Extraction:
    def __init__(self, stream, expected, advance, cancelled):
        self.stream = stream
        self.remaining = expected
        self.advance = advance
        self.cancelled = cancelled

    def write(self, data):
        check_cancel(self.cancelled)
        if len(data) > self.remaining:
            raise UnsafeTarget('ISO file exceeded its declared size.')
        count = self.stream.write(data)
        self.remaining -= count
        self.advance(count)
        return count


@contextmanager
def open_installer(snapshot, progress):
    import pycdlib
    from pycdlib.pycdlibexception import PyCdlibInvalidISO

    iso = pycdlib.PyCdlib()
    try:
        iso.open_fp(snapshot)
    except PyCdlibInvalidISO as exc:
        if str(exc) != 'Expected at least 2 UDF Anchors':
            raise
        from windows_udf import UdfReader

        progress('Inspecting Windows ISO with alternate UDF reader', 0, 0)
        with UdfReader().open(snapshot) as reader:
            yield reader.walk, reader.size, reader.copy
        return

    try:
        if iso.has_udf():
            key = 'udf_path'
        elif iso.has_joliet():
            key = 'joliet_path'
        else:
            raise UnsafeTarget('Windows installer mode requires a UDF or Joliet ISO.')
        yield (lambda: iso.walk(**{key: '/'}),
               lambda path: iso.get_record(**{key: path}).get_data_length(),
               lambda path, output: iso.get_file_from_iso_fp(output, **{key: path}))
    finally:
        iso.close()


def prepare_windows_image(snapshot, iso_size, work, capacity, progress, cancelled):
    tree = work / 'installer'
    tree.mkdir()
    progress('Inspecting Windows ISO', 0, 0)
    with open_installer(snapshot, progress) as (walk, size_of, copy):
        entries = installer_files(walk, size_of, iso_size, cancelled)
        done = 0
        total = sum(size or 0 for _, size in entries.values())

        def advance(count):
            nonlocal done
            done += count
            progress('Extracting Windows installer', done, total)

        for path, size in entries.values():
            check_cancel(cancelled)
            relative = path[1:].split('/')
            for name in relative:
                safe_name(name)
            destination = tree.joinpath(*relative)
            if size is None:
                destination.mkdir(parents=True, exist_ok=True)
                continue
            destination.parent.mkdir(parents=True, exist_ok=True)
            with destination.open('xb') as stream:
                extraction = Extraction(stream, size, advance, cancelled)
                copy(path, extraction)
                if extraction.remaining:
                    raise UnsafeTarget('ISO file was shorter than its declared size.')

    wim_path, wim_size = entries.get('/sources/install.wim', (None, None))
    if wim_size and wim_size > FAT_LIMIT:
        source = tree / wim_path[1:]
        if any(item.suffix.casefold() == '.swm' for item in source.parent.iterdir()):
            raise UnsafeTarget('The ISO already contains split Windows image files.')
        progress('Splitting Windows install.wim', 0, 0)
        run_tool(['/usr/bin/wimlib-imagex', 'split', str(source), str(source.parent / 'install.swm'),
                  '3800', '--check'], cancelled)
        source.unlink()

    progress('Building Windows FAT32 image', 0, 0)
    # Budget each file and
    # directory for cluster rounding, plus room for both FATs and long names.
    data_bytes = 0
    for item in tree.rglob('*'):
        check_cancel(cancelled)
        size = item.stat().st_size
        if size > FAT_LIMIT:
            raise UnsafeTarget('A Windows installer file still exceeds the FAT32 file size limit.')
        data_bytes += size + 4096
    partition_bytes = ((data_bytes + WORKSPACE_MARGIN + MIB - 1) // MIB) * MIB
    image_bytes = PARTITION_OFFSET + partition_bytes
    if image_bytes > capacity or image_bytes // 512 >= 2**32:
        raise UnsafeTarget('The prepared Windows installer does not fit on the selected USB.')
    image = work / 'windows.img'
    with image.open('xb') as disk:
        disk.truncate(image_bytes)
        mbr = bytearray(512)
        struct.pack_into('<I', mbr, 440, int.from_bytes(os.urandom(4), 'little') or 1)
        struct.pack_into('<B3sB3sII', mbr, 446, 0x80, b'\xfe\xff\xff',
                         0xEF, b'\xfe\xff\xff', PARTITION_OFFSET // 512, partition_bytes // 512)
        mbr[510:] = b'\x55\xaa'
        disk.write(mbr)

    run_tool(['/usr/sbin/mkfs.fat', '--offset=2048', '-F', '32', '-S', '512', '-s', '8',
              '-h', '2048', '-n', 'WINSETUP', str(image)], cancelled)
    for item in tree.iterdir():
        run_tool(['/usr/bin/mcopy', '-s', '-i', f'{image}@@{PARTITION_OFFSET}', str(item), '::/'],
                 cancelled)
    return image, image_bytes
