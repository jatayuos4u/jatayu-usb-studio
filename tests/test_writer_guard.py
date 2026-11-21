import tempfile
import unittest
from pathlib import Path
from writer_guard import guard

class GuardTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.iso = str(Path(self.tmp.name) / 'test.iso')
        Path(self.iso).write_bytes(b'ISO')
        self.disk = {'path':'/dev/sdb','type':'disk','tran':'usb','size':1024,
                     'children':[{'path':'/dev/sdb1','type':'part','mountpoints':[None]}]}
        self.snapshot = {'blockdevices':[self.disk]}
    def tearDown(self): self.tmp.cleanup()
    def test_valid_candidate_never_authorizes(self):
        r=guard(self.snapshot,'/dev/sdb',self.iso)
        self.assertTrue(r['candidate_checks_passed'])
        self.assertFalse(r['allowed_to_write'])
    def test_partition_blocked(self):
        self.assertFalse(guard(self.snapshot,'/dev/sdb1',self.iso)['candidate_checks_passed'])
    def test_mount_blocked(self):
        self.disk['children'][0]['mountpoints']=['/media/usb']
        self.assertFalse(guard(self.snapshot,'/dev/sdb',self.iso)['candidate_checks_passed'])
    def test_swap_blocked(self):
        self.disk['children'][0]['fstype']='swap'
        self.assertFalse(guard(self.snapshot,'/dev/sdb',self.iso)['candidate_checks_passed'])
    def test_internal_disk_blocked(self):
        self.disk['tran']='sata'
        self.assertFalse(guard(self.snapshot,'/dev/sdb',self.iso)['candidate_checks_passed'])
    def test_missing_device_blocked(self):
        self.assertFalse(guard(self.snapshot,'/dev/sdc',self.iso)['candidate_checks_passed'])
    def test_identity_change_blocked(self):
        self.assertFalse(guard(self.snapshot,'/dev/sdb',self.iso,device_identity='new',expected_identity='old')['candidate_checks_passed'])
    def test_oversize_iso_blocked(self):
        self.disk['size']=1
        self.assertFalse(guard(self.snapshot,'/dev/sdb',self.iso)['candidate_checks_passed'])
    def test_missing_iso_blocked(self):
        self.assertFalse(guard(self.snapshot,'/dev/sdb',self.iso+'missing')['candidate_checks_passed'])
