import os
import unittest
from unittest.mock import patch
from udisks2_fd_backend import request_readonly_fd
from udisks2_backend import DeviceRejected

class FDIntegrationTests(unittest.TestCase):
    def test_partition_rejected_before_opener(self):
        with self.assertRaises(ValueError):
            request_readonly_fd('/dev/sdb1', opener=lambda _: self.fail('opened'))
    def test_bad_inspection_rejected(self):
        with self.assertRaises(DeviceRejected):
            request_readonly_fd('/dev/sdb', inspect=lambda _: {'status':'UNKNOWN'}, opener=lambda _: self.fail('opened'))
    def test_regular_fd_rejected_and_closed(self):
        fd=os.open('/dev/null',os.O_RDONLY)
        evidence={'device':'/dev/sdb','status':'READ_ONLY_INSPECTED','size_bytes':1024}
        with self.assertRaises(DeviceRejected):
            request_readonly_fd('/dev/sdb',inspect=lambda _: evidence,opener=lambda _:fd)
        with self.assertRaises(OSError): os.fstat(fd)
    def test_no_write_calls(self):
        evidence={'device':'/dev/sdb','status':'READ_ONLY_INSPECTED','size_bytes':1024}
        with patch('udisks2_fd_backend.os.write',create=True,side_effect=AssertionError('write')):
            with self.assertRaises(DeviceRejected):
                request_readonly_fd('/dev/sdb',inspect=lambda _: evidence,opener=lambda _:os.open('/dev/null',os.O_RDONLY))
