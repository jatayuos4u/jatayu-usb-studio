import os
import stat
import unittest
from unittest.mock import patch, Mock
from beta91_experimental_writer import assert_open_target_identity, UnsafeTarget
from privileged_writer_contract import DeviceIdentity

IDENTITY = DeviceIdentity('/dev/sdz', 8, 240, '/sys/devices/usb/test', 1048576, 'usb', 'SERIAL')

class OpenFdBindingTests(unittest.TestCase):
    def test_valid_block_descriptor(self):
        fake = Mock(st_mode=stat.S_IFBLK | 0o600, st_rdev=os.makedev(8, 240))
        with patch('beta91_experimental_writer.os.fstat', return_value=fake), patch('beta91_experimental_writer.revalidate', return_value=True):
            self.assertTrue(assert_open_target_identity(10, IDENTITY))

    def test_reject_regular_file(self):
        fake = Mock(st_mode=stat.S_IFREG | 0o600, st_rdev=os.makedev(8, 240))
        with patch('beta91_experimental_writer.os.fstat', return_value=fake):
            with self.assertRaises(UnsafeTarget): assert_open_target_identity(10, IDENTITY)

    def test_reject_replaced_device(self):
        fake = Mock(st_mode=stat.S_IFBLK | 0o600, st_rdev=os.makedev(8, 241))
        with patch('beta91_experimental_writer.os.fstat', return_value=fake):
            with self.assertRaises(UnsafeTarget): assert_open_target_identity(10, IDENTITY)

    def test_reject_revalidation_failure(self):
        fake = Mock(st_mode=stat.S_IFBLK | 0o600, st_rdev=os.makedev(8, 240))
        with patch('beta91_experimental_writer.os.fstat', return_value=fake), patch('beta91_experimental_writer.revalidate', return_value=False):
            with self.assertRaises(UnsafeTarget): assert_open_target_identity(10, IDENTITY)
