import unittest
from dataclasses import replace
from pathlib import Path
from tempfile import TemporaryDirectory
from privileged_writer_contract import DeviceIdentity, DisabledPrivilegedWriter, revalidate

class ContractTests(unittest.TestCase):
    def setUp(self):
        self.identity = DeviceIdentity('/dev/sdb', 8, 16, '/sys/devices/usb1/block/sdb', 31000000000, 'usb', 'ABC')
    def test_same_identity(self):
        self.assertTrue(revalidate(self.identity, inspector=lambda p:self.identity))
    def test_changed_major_minor(self):
        self.assertFalse(revalidate(self.identity, inspector=lambda p:replace(self.identity, minor=32)))
    def test_changed_capacity(self):
        self.assertFalse(revalidate(self.identity, inspector=lambda p:replace(self.identity, size_bytes=100)))
    def test_changed_serial(self):
        self.assertFalse(revalidate(self.identity, inspector=lambda p:replace(self.identity, serial='NEW')))
    def test_changed_sysfs(self):
        self.assertFalse(revalidate(self.identity, inspector=lambda p:replace(self.identity, sysfs_path='/other')))
    def test_removed(self):
        self.assertFalse(revalidate(self.identity, inspector=lambda p:(_ for _ in ()).throw(FileNotFoundError())))
    def test_disabled_capabilities(self):
        self.assertFalse(DisabledPrivilegedWriter().capabilities()['writing_enabled'])
    def test_prepare_blocked(self):
        self.assertFalse(DisabledPrivilegedWriter().prepare({})['authorized'])
    def test_write_blocked(self):
        self.assertFalse(DisabledPrivilegedWriter().write({})['authorized'])
if __name__ == '__main__':
    unittest.main()
