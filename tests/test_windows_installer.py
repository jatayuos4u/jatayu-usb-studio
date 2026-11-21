import io
import shutil
import struct
import subprocess

import pytest

from studio_device_safety import UnsafeTarget
import windows_installer


def make_iso(path, *, udf, include_loader, install=b'install data'):
    pycdlib = pytest.importorskip('pycdlib')
    disc = pycdlib.PyCdlib()
    disc.new(interchange_level=3, joliet=3, udf='2.60' if udf else None)

    def names(relative):
        paths = {'iso_path': relative.upper(), 'joliet_path': relative}
        if udf:
            paths['udf_path'] = relative
        return paths

    for directory in ('/efi', '/efi/boot', '/sources'):
        disc.add_directory(**names(directory))
    files = {'/sources/boot.wim': b'boot data', '/sources/install.wim': install,
             '/setup.exe': b'setup data'}
    if include_loader:
        files['/efi/boot/bootx64.efi'] = b'efi loader data'
    for name, payload in files.items():
        paths = names(name)
        paths['iso_path'] += ';1'
        disc.add_fp(io.BytesIO(payload), len(payload), **paths)
    disc.write(str(path))
    disc.close()
    return files


@pytest.mark.parametrize('udf', [True, False])
def test_build_windows_fat32_image(tmp_path, udf):
    if not shutil.which('mcopy') or not shutil.which('mkfs.fat'):
        pytest.skip('Windows image tools are unavailable')
    source = tmp_path / 'Windows.iso'
    files = make_iso(source, udf=udf, include_loader=True)
    with source.open('rb') as snapshot:
        image, size = windows_installer.prepare_windows_image(
            snapshot, source.stat().st_size, tmp_path, 1024**3,
            lambda *_: None, lambda: False)
    with image.open('rb') as file:
        mbr = file.read(512)
    assert mbr[510:] == b'\x55\xaa'
    assert mbr[450] == 0xEF
    start, sectors = struct.unpack_from('<II', mbr, 454)
    assert start * 512 == windows_installer.PARTITION_OFFSET
    assert (start + sectors) * 512 == size == image.stat().st_size
    for name, payload in files.items():
        copied = subprocess.check_output(
            ['/usr/bin/mtype', '-i', f'{image}@@{start * 512}', '::' + name])
        assert copied == payload


def test_reject_image_without_windows_uefi_loader(tmp_path):
    source = tmp_path / 'image.iso'
    make_iso(source, udf=True, include_loader=False)
    with source.open('rb') as snapshot, pytest.raises(UnsafeTarget, match='missing the x64 UEFI'):
        windows_installer.prepare_windows_image(
            snapshot, source.stat().st_size, tmp_path, 1024**3,
            lambda *_: None, lambda: False)
    assert not (tmp_path / 'windows.img').exists()


@pytest.mark.parametrize('name', ['..', 'a/b', r'a\b', 'CON.txt', 'file*', 'file.'])
def test_reject_unsafe_fat_names(name):
    with pytest.raises(UnsafeTarget, match='cannot be copied safely'):
        windows_installer.safe_name(name)


def test_large_wim_conversion(tmp_path, monkeypatch):
    if not all(shutil.which(tool) for tool in ('mcopy', 'mkfs.fat', 'wimlib-imagex')):
        pytest.skip('Windows image tools are unavailable')
    content = tmp_path / 'wim-contents'
    content.mkdir()
    (content / 'fixture.txt').write_text('fixture')
    wim = tmp_path / 'fixture.wim'
    subprocess.run(['/usr/bin/wimlib-imagex', 'capture', str(content), str(wim), 'Fixture'],
                   check=True, capture_output=True)
    source = tmp_path / 'Windows.iso'
    make_iso(source, udf=True, include_loader=True, install=wim.read_bytes())
    # Trigger splitting on a small, valid WIM, then restore the real FAT32
    # limit for validating the output of wimlib.
    run_tool = windows_installer.run_tool

    def run_and_restore_limit(arguments, cancelled):
        run_tool(arguments, cancelled)
        if arguments[1] == 'split':
            monkeypatch.setattr(windows_installer, 'FAT_LIMIT', 2**32 - 1)

    monkeypatch.setattr(windows_installer, 'run_tool', run_and_restore_limit)
    monkeypatch.setattr(windows_installer, 'FAT_LIMIT', wim.stat().st_size - 1)
    with source.open('rb') as snapshot:
        image, _ = windows_installer.prepare_windows_image(
            snapshot, source.stat().st_size, tmp_path, 1024**3,
            lambda *_: None, lambda: False)

    image_arg = f'{image}@@{windows_installer.PARTITION_OFFSET}'
    split = tmp_path / 'result.swm'
    split.write_bytes(subprocess.check_output(
        ['/usr/bin/mtype', '-i', image_arg, '::/sources/install.swm']))
    subprocess.run(['/usr/bin/wimlib-imagex', 'verify', str(split)],
                   check=True, capture_output=True)
    assert subprocess.run(['/usr/bin/mtype', '-i', image_arg, '::/sources/install.wim'],
                          capture_output=True).returncode != 0


@pytest.mark.parametrize('keep_primary', [True, False])
def test_incomplete_udf_anchor_set(tmp_path, keep_primary):
    if not shutil.which('mcopy') or not shutil.which('mkfs.fat'):
        pytest.skip('Windows image tools are unavailable')
    source = tmp_path / 'Windows.iso'
    files = make_iso(source, udf=True, include_loader=True)
    size = source.stat().st_size
    last = size // 2048 - 1
    with source.open('r+b') as stream:
        for sector in (last - 256, last, 256):
            if sector == 256 and keep_primary:
                continue
            stream.seek(sector * 2048)
            if stream.read(2) == b'\x02\x00':
                stream.seek(sector * 2048)
                stream.write(bytes(2048))

    phases = []

    def prepare():
        with source.open('rb') as snapshot:
            return windows_installer.prepare_windows_image(
                snapshot, size, tmp_path, 1024**3,
                lambda phase, *_: phases.append(phase), lambda: False)

    if keep_primary:
        image, _ = prepare()
        for name, payload in files.items():
            copied = subprocess.check_output([
                '/usr/bin/mtype', '-i', f'{image}@@1048576', '::' + name])
            assert copied == payload
    else:
        with pytest.raises(UnsafeTarget, match='Could not read the Windows ISO UDF volume'):
            prepare()
        assert not (tmp_path / 'windows.img').exists()
    assert 'Inspecting Windows ISO with alternate UDF reader' in phases
