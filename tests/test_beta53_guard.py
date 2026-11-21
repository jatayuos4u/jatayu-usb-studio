import unittest
import tempfile
from pathlib import Path
from beta53_device_guard import validate_snapshot, verify_regular_file_only, DeviceChanged

class GuardTests(unittest.TestCase):
    def setUp(self):
        self.snap={'path':'/dev/sdb','major_minor':'8:16','size':100000,'serial':'A','model':'B','vendor':'C','transport':'usb','partitions':[]}
    def test_matching(self):
        self.assertFalse(validate_snapshot(self.snap,self.snap.copy())['authorized'])
    def test_changed_identity(self):
        other=self.snap.copy();other['serial']='X'
        with self.assertRaises(DeviceChanged):validate_snapshot(self.snap,other)
    def test_missing_identity(self):
        other=self.snap.copy();del other['serial']
        with self.assertRaises(DeviceChanged):validate_snapshot(self.snap,other)
    def test_reject_invalid_capacity(self):
        other=self.snap.copy();other['size']=0
        with self.assertRaises(DeviceChanged):validate_snapshot(other,other)
    def test_regular_file(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'test';p.write_bytes(b'abc')
            self.assertFalse(verify_regular_file_only(p)['writing_enabled'])
    def test_symlink_denied(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'test';p.write_bytes(b'abc');q=Path(d)/'link';q.symlink_to(p)
            with self.assertRaises(DeviceChanged):verify_regular_file_only(q)
    def test_directory_denied(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(DeviceChanged):verify_regular_file_only(d)
