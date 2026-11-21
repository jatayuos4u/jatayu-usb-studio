import hashlib
import os
import tempfile
import unittest
from dataclasses import replace
from beta64_authorization import Denied
from beta76_trusted_preflight import BusCredentials, DeviceSnapshot, TrustedPreflight

C = BusCredentials(':1.75', 1000, 1234)
D = DeviceSnapshot('/dev/sdb', '8:16', '/sys/devices/pci0000:00/usb1', 31029460992, True, False, False, False, True)

class PreflightTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = os.path.join(self.temp.name, 'test.iso')
        self.payload = b'ISO test bytes' * 100
        with open(self.path, 'wb') as f: f.write(self.payload)
        self.kw = dict(observed_sender=':1.75', credentials=C, device=D, iso_path=self.path,
                       expected_iso_sha256=hashlib.sha256(self.payload).hexdigest(),
                       expected_iso_size=len(self.payload))
        self.verifier = TrustedPreflight()
    def test_good_snapshot(self):
        self.assertEqual(self.verifier.verify(**self.kw).uid, 1000)
    def test_sender_spoof(self):
        with self.assertRaises(Denied): self.verifier.verify(**(self.kw | {'observed_sender': ':1.76'}))
    def test_missing_credentials(self):
        with self.assertRaises(Denied): self.verifier.verify(**(self.kw | {'credentials': None}))
    def test_root_caller(self):
        with self.assertRaises(Denied): self.verifier.verify(**(self.kw | {'credentials': replace(C, uid=0)}))
    def test_partition_rejected(self):
        with self.assertRaises(Denied): self.verifier.verify(**(self.kw | {'device': replace(D, whole_disk=False)}))
    def test_internal_disk_rejected(self):
        with self.assertRaises(Denied): self.verifier.verify(**(self.kw | {'device': replace(D, removable=False)}))
    def test_mounted_rejected(self):
        with self.assertRaises(Denied): self.verifier.verify(**(self.kw | {'device': replace(D, mounted=True)}))
    def test_system_disk_rejected(self):
        with self.assertRaises(Denied): self.verifier.verify(**(self.kw | {'device': replace(D, system_disk=True)}))
    def test_read_only_rejected(self):
        with self.assertRaises(Denied): self.verifier.verify(**(self.kw | {'device': replace(D, read_only=True)}))
    def test_changed_device_rejected(self):
        with self.assertRaises(Denied): self.verifier.verify(**(self.kw | {'expected_device': replace(D, size=100)}))
    def test_iso_digest_mismatch(self):
        with self.assertRaises(Denied): self.verifier.verify(**(self.kw | {'expected_iso_sha256': 'a'*64}))
    def test_iso_size_mismatch(self):
        with self.assertRaises(Denied): self.verifier.verify(**(self.kw | {'expected_iso_size': 1}))
    def test_iso_symlink_rejected(self):
        link = os.path.join(self.temp.name, 'link.iso')
        os.symlink(self.path, link)
        with self.assertRaises(Denied): self.verifier.verify(**(self.kw | {'iso_path': link}))
    def test_no_writing(self):
        with self.assertRaises(Denied): self.verifier.request_write('/dev/sdb')
