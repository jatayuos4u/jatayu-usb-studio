import subprocess
import unittest
from udisks2_backend import object_path, probe

class TestUDisks2Boundary(unittest.TestCase):
    def test_canonical_disk(self):
        self.assertEqual(object_path('/dev/sdb'), '/org/freedesktop/UDisks2/block_devices/sdb')
    def test_no_partition(self):
        for device in ['/dev/sdb1','/dev/mapper/root','/dev/../sda','/tmp/disk','/dev/sda;rm','/dev/nvme0n1p1']:
            with self.subTest(device=device), self.assertRaises(ValueError): object_path(device)
    def test_no_write_on_success(self):
        calls=[]
        def run(args, **kw):
            calls.append(args)
            return subprocess.CompletedProcess(args,0,'s "2.10"','')
        self.assertEqual(probe(runner=run)['writing_enabled'],False)
        self.assertEqual(calls[0][3],'get-property')
    def test_unavailable_fails_closed(self):
        def run(args, **kw): raise subprocess.TimeoutExpired(args,4)
        self.assertFalse(probe(runner=run)['available'])
        self.assertFalse(probe(runner=run)['writing_enabled'])
