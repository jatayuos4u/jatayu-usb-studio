import os
import unittest
from unittest.mock import patch
from types import SimpleNamespace
from udisks2_write_boundary import inspect_writable_boundary, WriteBoundaryRejected
from udisks2_backend import DeviceRejected

DEVICE = '/dev/sdb'
EVIDENCE = {'device': DEVICE, 'status': 'READ_ONLY_INSPECTED', 'size_bytes': 4096}

class TestWritableBoundary(unittest.TestCase):
    def test_invalid_device_rejected_before_open(self):
        with self.assertRaises(ValueError):
            inspect_writable_boundary('/dev/sdb1', inspect=lambda _: EVIDENCE, opener=lambda _: 5)

    def test_untrusted_evidence_rejected_before_open(self):
        with self.assertRaises(DeviceRejected):
            inspect_writable_boundary(DEVICE, inspect=lambda _: {'status': 'UNKNOWN'}, opener=lambda _: 5)

    def test_regular_file_descriptor_rejected_and_closed(self):
        fd = os.open('/dev/null', os.O_RDWR)
        with self.assertRaises(WriteBoundaryRejected):
            inspect_writable_boundary(DEVICE, inspect=lambda _: EVIDENCE, opener=lambda _: fd)
        with self.assertRaises(OSError):
            os.fstat(fd)

    def test_topology_change_rejected_and_closed(self):
        fd = os.open('/dev/null', os.O_RDWR)
        checks = iter((EVIDENCE, {'device': DEVICE, 'status': 'CHANGED'}))
        fake_stat = SimpleNamespace(st_mode=0o060000, st_rdev=os.makedev(8,16))
        with patch('udisks2_write_boundary.os.fstat', return_value=fake_stat), \
             patch('udisks2_write_boundary.os.stat', return_value=fake_stat), \
             patch('udisks2_write_boundary.fcntl.fcntl', return_value=os.O_RDWR):
            with self.assertRaises(WriteBoundaryRejected):
                inspect_writable_boundary(DEVICE, inspect=lambda _: next(checks), opener=lambda _: fd)
        with self.assertRaises(OSError):
            os.fstat(fd)

    def test_valid_attestation_never_returns_fd(self):
        fd = os.open('/dev/null', os.O_RDWR)
        fake_stat = SimpleNamespace(st_mode=0o060000, st_rdev=os.makedev(8,16))
        with patch('udisks2_write_boundary.os.fstat', return_value=fake_stat), \
             patch('udisks2_write_boundary.os.stat', return_value=fake_stat), \
             patch('udisks2_write_boundary.fcntl.fcntl', return_value=os.O_RDWR):
            result = inspect_writable_boundary(DEVICE, inspect=lambda _: EVIDENCE, opener=lambda _: fd)
        self.assertFalse(result['writing_enabled'])
        self.assertNotIn('fd', result)
        with self.assertRaises(OSError):
            os.fstat(fd)
