import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from privileged_writer_contract import DeviceIdentity
from beta89_writer_preflight import validate_target, PreflightRejected

class TestPreflight(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
        node=self.root/'class/block/sdb'
        node.mkdir(parents=True)
        (node/'removable').write_text('1')
        child=node/'sdb1'
        child.mkdir()
        (child/'partition').write_text('1')
        (child/'dev').write_text('8:17')
        self.identity=DeviceIdentity('/dev/sdb',8,16,'/sys/mock',31029460992,'usb','test')
        self.inspect=lambda p:self.identity
    def run_check(self, **kwargs):
        return validate_target('/dev/sdb',inspector=self.inspect,sysroot=self.root,
                               mountinfo=kwargs.pop('mountinfo','24 1 0:23 / / rw - tmpfs tmpfs rw'),**kwargs)
    def test_good_is_never_authorization(self):
        result=self.run_check()
        self.assertEqual(result['status'],'PREFLIGHT_ONLY')
        self.assertFalse(result['authorized'])
        self.assertFalse(result['writing_enabled'])
    def test_mounted_partition_blocked(self):
        with self.assertRaises(PreflightRejected):
            self.run_check(mountinfo='30 1 8:17 / /media/usb rw - vfat /dev/sdb1 rw')
    def test_mounted_disk_blocked(self):
        with self.assertRaises(PreflightRejected):
            self.run_check(mountinfo='30 1 8:16 / /media/usb rw - ext4 /dev/sdb rw')
    def test_nonremovable_blocked(self):
        (self.root/'class/block/sdb/removable').write_text('0')
        with self.assertRaises(PreflightRejected): self.run_check()
    def test_missing_removable_blocked(self):
        (self.root/'class/block/sdb/removable').unlink()
        with self.assertRaises(PreflightRejected): self.run_check()
    def test_malformed_mount_blocked(self):
        with self.assertRaises(PreflightRejected):
            self.run_check(mountinfo='bad')
    def test_identity_mismatch_blocked(self):
        self.identity=DeviceIdentity('/dev/sda',8,0,'/sys/mock',31029460992,'usb','test')
        with self.assertRaises(PreflightRejected): self.run_check()
    def test_non_usb_blocked(self):
        self.identity=DeviceIdentity('/dev/sdb',8,16,'/sys/mock',31029460992,'sata','test')
        with self.assertRaises(PreflightRejected): self.run_check()
    def test_nested_path_blocked(self):
        with self.assertRaises(PreflightRejected):
            validate_target('/dev/disk/by-id/anything',inspector=self.inspect,sysroot=self.root,mountinfo='')
