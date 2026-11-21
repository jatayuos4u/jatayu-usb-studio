import asyncio
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch
from beta64_authorization import Denied
from beta77_live_evidence import snapshot_device, credentials_from_transport, request_write

class LiveEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        self.block = self.base/'sys/class/block/sdb'
        self.block.mkdir(parents=True)
        for name, value in {'dev':'8:16','size':'1000','removable':'1','ro':'0'}.items():
            (self.block/name).write_text(value)
        proc = self.base/'proc/self'
        proc.mkdir(parents=True)
        (proc/'mountinfo').write_text('24 23 0:23 / / rw - tmpfs tmpfs rw\n')
        (self.base/'proc/swaps').write_text('Filename Type Size Used Priority\n')
    def collect(self, path='/dev/sdb'):
        return snapshot_device(path,sys_root=str(self.base/'sys'),proc_root=str(self.base/'proc'))
    def test_clean_removable(self):
        d=self.collect()
        self.assertTrue(d.removable)
        self.assertFalse(d.mounted)
        self.assertEqual(d.size,512000)
    def test_reject_partition(self):
        (self.block/'partition').write_text('1')
        with self.assertRaises(Denied): self.collect()
    def test_reject_invalid_path(self):
        with self.assertRaises(Denied): self.collect('/dev/../sda')
    def test_mount_on_disk(self):
        (self.base/'proc/self/mountinfo').write_text('24 23 8:16 / /mnt rw - ext4 /dev/sdb rw\n')
        self.assertTrue(self.collect().system_disk)
    def test_mount_on_partition(self):
        child=self.block/'sdb1';child.mkdir()
        (child/'partition').write_text('1');(child/'dev').write_text('8:17')
        (self.base/'proc/self/mountinfo').write_text('24 23 8:17 / /mnt rw - ext4 /dev/sdb1 rw\n')
        self.assertTrue(self.collect().mounted)
    def test_swap(self):
        (self.base/'proc/swaps').write_text('Filename Type Size Used Priority\n/dev/sdb2 partition 1000 0 -2\n')
        self.assertTrue(self.collect().system_disk)
    def test_unknown_mountinfo(self):
        (self.base/'proc/self/mountinfo').write_text('corrupt')
        with self.assertRaises(Denied): self.collect()
    def test_missing_inventory(self):
        (self.block/'size').unlink()
        with self.assertRaises(Denied): self.collect()
    def test_request_write_denied(self):
        with self.assertRaises(Denied): request_write('/dev/sdb')
    def test_bus_sender_from_envelope(self):
        identity=SimpleNamespace(unique_name=':1.20',uid=1000,pid=123)
        async def run():
            with patch('beta77_live_evidence.resolve_sender',new=AsyncMock(return_value=identity)):
                return await credentials_from_transport(object(),SimpleNamespace(sender=':1.20'))
        self.assertEqual(asyncio.run(run()).uid,1000)
    def test_bus_sender_mismatch(self):
        identity=SimpleNamespace(unique_name=':1.21',uid=1000,pid=123)
        async def run():
            with patch('beta77_live_evidence.resolve_sender',new=AsyncMock(return_value=identity)):
                await credentials_from_transport(object(),SimpleNamespace(sender=':1.20'))
        with self.assertRaises(Denied): asyncio.run(run())
    def test_bus_sender_missing(self):
        with self.assertRaises(Denied): asyncio.run(credentials_from_transport(object(),SimpleNamespace(sender=None)))
