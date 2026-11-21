"""RC1 regression checks. Every transfer fixture is a regular file."""
import hashlib
import io
from contextlib import contextmanager
import os
from pathlib import Path
import shutil
import subprocess
from types import SimpleNamespace

import pytest

import studio_operations as studio


def iso_bytes():
    image = bytearray(20 * 2048)
    image[16 * 2048:16 * 2048 + 7] = b'\x01CD001\x01'
    from struct import pack_into
    pack_into("<I", image, 16 * 2048 + 80, 20)
    pack_into(">I", image, 16 * 2048 + 84, 20)
    pack_into("<H", image, 16 * 2048 + 128, 2048)
    pack_into(">H", image, 16 * 2048 + 130, 2048)
    return bytes(image)


def no_progress(*args):
    pass


def not_cancelled():
    return False


class Response(io.BytesIO):
    status = 200

    def __init__(self, data, *, url='https://example.invalid/test.iso', length=None):
        super().__init__(data)
        self.url = url
        self.headers = {'Content-Length': str(len(data) if length is None else length)}

    def geturl(self):
        return self.url


def download(tmp_path, response, cancelled=not_cancelled):
    return studio.download_iso('https://example.invalid/test.iso', tmp_path, no_progress,
                               cancelled, opener=lambda url, timeout: response)


def test_download_publishes_exact_iso_and_hash(tmp_path):
    image = iso_bytes()
    result = download(tmp_path, Response(image))
    assert result['status'] == 'DOWNLOADED'
    assert result['sha256'] == hashlib.sha256(image).hexdigest()
    assert Path(result['path']).read_bytes() == image
    assert len(list(tmp_path.iterdir())) == 1


@pytest.mark.parametrize('url', ['http://example.invalid/test.iso',
                                 'https://name:pass@example.invalid/test.iso', 'file:///tmp/a.iso'])
def test_download_rejects_invalid_scheme_or_credentials(url):
    with pytest.raises(ValueError, match='HTTPS'):
        studio.https_url(url)


def test_download_redirect_handler_rejects_http():
    handler = studio.HttpsRedirect()
    with pytest.raises(ValueError, match='HTTPS'):
        handler.redirect_request(None, None, 302, '', {}, 'http://example.invalid/test.iso')


@pytest.mark.parametrize('response', [
    Response(b'not an image'), Response(iso_bytes(), length=999999),
    Response(iso_bytes(), url='http://example.invalid/test.iso'),
])
def test_failed_download_does_not_publish(tmp_path, response):
    with pytest.raises((ValueError, studio.UnsafeTarget)):
        download(tmp_path, response)
    assert not list(tmp_path.iterdir())


def test_cancelled_download_removes_partial_file(tmp_path):
    with pytest.raises(studio.WriteCancelled):
        download(tmp_path, Response(iso_bytes()), cancelled=lambda: True)
    assert not list(tmp_path.iterdir())


def test_download_preserves_existing_file(tmp_path):
    existing = tmp_path / 'test.iso'
    existing.write_bytes(b'keep this')
    with pytest.raises(FileExistsError):
        download(tmp_path, Response(iso_bytes()))
    assert existing.read_bytes() == b'keep this'


@pytest.fixture
def disks(tmp_path, monkeypatch):
    path, source = '/dev/sdz', '/dev/sdy'
    disk = tmp_path / 'disk.img'
    original = tmp_path / 'source.img'
    size = 64 * 1024 * 1024
    for file in (disk, original):
        with file.open('wb') as out:
            out.truncate(size)
    node = tmp_path / 'sysfs'
    (node / 'queue').mkdir(parents=True)
    (node / 'queue' / 'logical_block_size').write_text('512')
    target_id = SimpleNamespace(path=path, major=8, minor=16, size_bytes=size, sysfs_path=str(node))
    source_id = SimpleNamespace(path=source, major=8, minor=32, size_bytes=size, sysfs_path=str(node))
    modes = []

    def inspect(device, sequence):
        assert sequence in (23, 33)
        return {path: target_id, source: source_id}[device]

    @contextmanager
    def opener(device, sequence, identity, *, writable, cancelled):
        modes.append((device, writable))
        with (disk if device == path else original).open('r+b' if writable else 'rb') as fake:
            yield fake.fileno()

    monkeypatch.setattr(studio, 'inspect_selection', inspect)
    monkeypatch.setattr(studio, 'open_usb', opener)
    monkeypatch.setattr(studio, 'require_fd_generation', lambda *args: None)
    monkeypatch.setattr(studio, 'attest_fd', lambda *args, **kwargs: True)
    args = SimpleNamespace(device=path, sequence=23, source=source, source_sequence=33,
                           iso=tmp_path / 'test.iso', partition=None)
    args.iso.write_bytes(iso_bytes())
    return args, disk, original, modes


def test_file_backed_write_and_usb_verify(disks):
    args, disk, _, modes = disks
    args.operation = 'write'
    result = studio.disk_operation(args, no_progress, not_cancelled)
    assert result['status'] == 'WRITTEN_AND_VERIFIED'
    args.operation = 'verify'
    assert studio.disk_operation(args, no_progress, not_cancelled)['status'] == 'IMAGE_MATCH'
    assert modes == [(args.device, True), (args.device, False)]
    with disk.open('r+b') as out:
        out.write(b'mismatch')
    with pytest.raises(studio.UnsafeTarget, match='mismatch'):
        studio.disk_operation(args, no_progress, not_cancelled)


def test_file_backed_clone_and_overlap_rejection(disks):
    args, disk, source, modes = disks
    with source.open('r+b') as out:
        out.write(b'clone source')
    args.operation = 'clone'
    result = studio.disk_operation(args, no_progress, not_cancelled)
    assert result['status'] == 'WRITTEN_AND_VERIFIED'
    with disk.open('rb') as copy:
        assert copy.read(12) == b'clone source'
    assert modes == [(args.source, False), (args.device, True)]
    args.source = args.device
    with pytest.raises(studio.UnsafeTarget, match='distinct'):
        studio.disk_operation(args, no_progress, not_cancelled)


@pytest.mark.parametrize('filesystem', studio.FILESYSTEMS)
def test_file_backed_format_and_health_check(disks, filesystem):
    args, disk, _, modes = disks
    tools = studio.FILESYSTEMS[filesystem]
    if not all(Path(tool).is_file() for tool in (tools[0], tools[2], '/usr/sbin/blkid')):
        pytest.skip('Filesystem utilities are unavailable')
    args.operation = 'format'
    args.filesystem = filesystem
    args.full_format = True
    result = studio.filesystem_operation(args, no_progress, not_cancelled)
    assert result['status'] == 'WRITTEN_AND_VERIFIED'
    assert result['bytes'] == disk.stat().st_size
    args.operation = 'check'
    result = studio.filesystem_operation(args, no_progress, not_cancelled)
    assert result['status'] == 'FILESYSTEM_CLEAN', result
    assert modes == [(args.device, True), (args.device, False)]


def test_quick_fat32_format_preserves_middle_and_checks_clean(disks):
    args, disk, _, _ = disks
    args.operation, args.filesystem = 'format', 'vfat'
    size = disk.stat().st_size
    with disk.open('r+b') as target:
        for offset in (size // 2, size - 512):
            target.seek(offset)
            target.write(b'old data')
    result = studio.filesystem_operation(args, no_progress, not_cancelled)
    assert result['status'] == 'QUICK_FORMAT_VERIFIED'
    with disk.open('r+b') as handle:
        os.fchmod(handle.fileno(), 0)
        try:
            if os.geteuid() != 0:
                reopened = subprocess.run(
                    ['/usr/sbin/blkid', '-p', f'/proc/self/fd/{handle.fileno()}'],
                    pass_fds=(handle.fileno(),), capture_output=True, check=False)
                assert reopened.returncode != 0
            studio.verify_fat_filesystem(handle.fileno())
        finally:
            os.fchmod(handle.fileno(), 0o600)
    assert result['bytes'] < size
    with disk.open('rb') as target:
        target.seek(size // 2)
        assert target.read(8) == b'old data'
        target.seek(size - 512)
        assert target.read(8) == bytes(8)
    args.operation = 'check'
    assert studio.filesystem_operation(args, no_progress, not_cancelled)['status'] == 'FILESYSTEM_CLEAN'


def test_file_backed_partition_repair_preserves_neighbor_bytes(disks, tmp_path):
    args, disk, _, modes = disks
    debugfs = '/usr/sbin/debugfs'
    dependencies = ['/usr/sbin/mkfs.ext4', '/usr/sbin/e2fsck', '/usr/sbin/blkid', debugfs]
    if not all(Path(path).is_file() for path in dependencies):
        pytest.skip('ext4 utilities are unavailable')
    partition = tmp_path / 'partition.img'
    with partition.open('wb') as output:
        output.truncate(32 * 1024 * 1024)
    subprocess.run(['/usr/sbin/mkfs.ext4', '-F', str(partition)], check=True, capture_output=True)
    subprocess.run([debugfs, '-w', '-R', 'setb 15000', str(partition)], check=True, capture_output=True)
    start = 1024 * 1024
    node = tmp_path / 'sysfs' / 'sdz1'
    node.mkdir()
    (node / 'partition').write_text('1')
    (node / 'start').write_text(str(start // 512))
    (node / 'size').write_text(str(partition.stat().st_size // 512))
    with disk.open('r+b') as drive, partition.open('rb') as part:
        drive.write(b'keep start')
        drive.seek(start)
        shutil.copyfileobj(part, drive)
        drive.write(b'keep end')
    args.partition = '/dev/sdz1'
    args.operation = 'check'
    assert studio.filesystem_operation(args, no_progress, not_cancelled)['status'] == 'FILESYSTEM_FINDINGS'
    args.operation = 'repair'
    result = studio.filesystem_operation(args, no_progress, not_cancelled)
    assert result['status'] == 'WRITTEN_AND_VERIFIED', result
    with disk.open('rb') as drive:
        assert drive.read(10) == b'keep start'
        drive.seek(start + partition.stat().st_size)
        assert drive.read(8) == b'keep end'
    assert modes == [(args.device, False), (args.device, True)]


def test_replacement_generation_fails_before_inspection(monkeypatch):
    monkeypatch.setattr(studio, 'disk_sequence', lambda device: 33)
    with pytest.raises(studio.UnsafeTarget, match='replaced'):
        studio.inspect_selection('/dev/sdz', 23)


def test_opened_regular_file_is_refused(tmp_path):
    with (tmp_path / 'not-a-block-device').open('w+b') as descriptor:
        with pytest.raises(studio.UnsafeTarget, match='different device'):
            studio.attest_fd(descriptor.fileno(), SimpleNamespace(major=8, minor=16), 23, writable=True)


def test_swap_file_backing_device_blocks_operation():
    current = SimpleNamespace(st_mode=0o100600, st_dev=os.makedev(8, 17))
    with pytest.raises(studio.UnsafeTarget, match='active swap'):
        from beta91_experimental_writer import reject_active_swap
        reject_active_swap({(8, 17)}, swaps_text=(
            'Filename Type Size Used Priority\n/media/swap\\040file file 10 0 -2\n'),
            stat_device=lambda path: current if path == '/media/swap file' else None)


def test_unconfirmed_write_leaves_destination_unchanged(disks):
    args, disk, _, modes = disks
    args.operation = 'write'

    def refuse():
        raise studio.WriteCancelled('Operator declined')

    with pytest.raises(studio.WriteCancelled, match='declined'):
        studio.disk_operation(args, no_progress, not_cancelled, confirm_write=refuse)
    with disk.open('rb') as destination:
        assert destination.read(len(iso_bytes())) == bytes(len(iso_bytes()))
    assert modes == [(args.device, True)]


def test_successful_local_tls_and_untrusted_certificate_rejected(tmp_path, monkeypatch):
    from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
    import ssl
    import threading
    import urllib.error

    if not shutil.which('openssl'):
        pytest.skip('OpenSSL command unavailable')
    cert, key = tmp_path / 'test-cert.pem', tmp_path / 'test-key.pem'
    subprocess.run(['openssl', 'req', '-x509', '-nodes', '-newkey', 'rsa:2048',
                    '-days', '1', '-subj', '/CN=localhost',
                    '-addext', 'subjectAltName=IP:127.0.0.1',
                    '-keyout', str(key), '-out', str(cert)], check=True, capture_output=True)

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            body = iso_bytes()
            self.send_response(200)
            self.send_header('Content-Length', str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    try:
        server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
    except OSError as exc:
        pytest.skip(f'Loopback socket unavailable: {exc}')
    with server:
        tls = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        tls.load_cert_chain(cert, key)
        server.socket = tls.wrap_socket(server.socket, server_side=True)
        task = threading.Thread(target=server.serve_forever, daemon=True)
        task.start()
        try:
            monkeypatch.setenv('no_proxy', 'localhost,127.0.0.1')
            destination = tmp_path / 'downloads'
            destination.mkdir()
            url = f'https://127.0.0.1:{server.server_port}/release.iso'
            with pytest.raises(urllib.error.URLError) as failure:
                studio.download_iso(url, destination, no_progress, not_cancelled)
            assert isinstance(failure.value.reason, ssl.SSLCertVerificationError)
            assert not list(destination.iterdir())
            monkeypatch.setenv('SSL_CERT_FILE', str(cert))
            assert studio.download_iso(url, destination, no_progress, not_cancelled)['status'] == 'DOWNLOADED'
            assert (destination / 'release.iso').read_bytes() == iso_bytes()
        finally:
            server.shutdown()
            task.join()


@pytest.mark.parametrize("write_access", [False, True])
def test_gio_request_uses_exclusive_descriptor_and_binds_mode(tmp_path, monkeypatch, write_access):
    pytest.importorskip('gi')
    from gi.repository import Gio, GLib
    path = tmp_path / 'fixture.img'
    path.write_bytes(b'fixture')
    identity = SimpleNamespace(path='/dev/sdz')
    seen = []
    monkeypatch.setattr(studio, 'inspect_selection', lambda *args: identity)

    def attest(fd, expected, sequence, *, writable):
        assert expected == identity and sequence == 23 and writable == write_access
        assert os.pread(fd, 7, 0) == b'fixture'
        seen.append(fd)

    def call(service, object_path, interface, method, parameters,
             reply_type, flags, timeout, input_fds, cancellable):
        assert service == 'org.freedesktop.UDisks2'
        assert object_path.endswith('/sdz') and interface.endswith('.Block')
        assert method == 'OpenDevice'
        assert flags == Gio.DBusCallFlags.ALLOW_INTERACTIVE_AUTHORIZATION
        assert parameters.unpack() == ('rw' if write_access else 'r', {'flags': os.O_EXCL | os.O_NOFOLLOW})
        descriptors = Gio.UnixFDList.new()
        with path.open('r+b' if write_access else 'rb') as file:
            index = descriptors.append(file.fileno())
        return GLib.Variant('(h)', (index,)), descriptors

    monkeypatch.setattr(studio, 'attest_fd', attest)
    monkeypatch.setattr(Gio, 'bus_get_sync', lambda *args: SimpleNamespace(call_with_unix_fd_list_sync=call))
    with studio.open_usb(identity.path, 23, identity, writable=write_access, cancelled=not_cancelled) as fd:
        assert fd == seen[0]
    with pytest.raises(OSError):
        os.fstat(fd)


def test_iso_stage_uses_home_when_temp_is_full(tmp_path, monkeypatch):
    from types import SimpleNamespace
    import studio_device_safety as safety

    temp = tmp_path / 'temp'
    home = tmp_path / 'home'
    temp.mkdir()
    home.mkdir()
    monkeypatch.setattr(safety.tempfile, 'gettempdir', lambda: str(temp))
    monkeypatch.setattr(safety.Path, 'home', lambda: home)
    monkeypatch.setattr(safety.os, 'statvfs', lambda path: SimpleNamespace(
        f_frsize=1, f_bavail=100 if path == home else 0))
    snapshot, directory = safety.open_iso_snapshot(50)
    with snapshot:
        assert directory == home
    with studio.filesystem_workspace(50) as folder:
        assert Path(folder).parent == home
    with pytest.raises(safety.UnsafeTarget, match='No data was written to the target USB'):
        safety.open_iso_snapshot(101)


def test_repair_checks_snapshot_space_before_usb_open(disks, monkeypatch):
    args, disk, _, modes = disks
    args.operation = 'repair'
    monkeypatch.setattr(studio, 'snapshot_locations', lambda size: iter(()))
    with pytest.raises(studio.UnsafeTarget, match=f'{disk.stat().st_size:,} bytes.*'):
        studio.filesystem_operation(args, no_progress, not_cancelled)
    assert modes == []


@pytest.mark.parametrize('consistent', [True, False])
def test_udisks_health_check_uses_no_snapshot(disks, monkeypatch, consistent):
    pytest.importorskip('gi')
    from gi.repository import Gio, GLib

    args, _, _, modes = disks
    args.operation = 'check'

    def call(service, path, interface, method, *rest):
        assert (service, path, interface, method) == (
            studio.SERVICE, studio.object_path(args.device),
            studio.SERVICE + '.Filesystem', 'Check')
        return GLib.Variant('(b)', (consistent,))

    monkeypatch.setattr(Gio, 'bus_get_sync', lambda *args: SimpleNamespace(call_sync=call))
    monkeypatch.setattr(studio, 'filesystem_workspace', lambda *args: pytest.fail('Unexpected snapshot'))
    result = studio.check_filesystem(args, no_progress, not_cancelled)
    assert result['status'] == ('FILESYSTEM_CLEAN' if consistent else 'FILESYSTEM_FINDINGS')
    assert modes == []


def test_windows_iso_is_rejected_before_usb_open(disks, monkeypatch):
    args, _, _, modes = disks
    image = bytearray(iso_bytes())
    image[16 * 2048 + 8:16 * 2048 + 17] = b'Microsoft'
    path = Path(args.iso)
    path.write_bytes(image)
    args.operation = 'write'
    monkeypatch.setattr('studio_device_safety.open_iso_snapshot', lambda *_: pytest.fail('Windows ISO was staged'))
    with pytest.raises(studio.UnsafeTarget, match='Windows installer ISO'):
        studio.disk_operation(args, no_progress, not_cancelled)
    assert modes == []
