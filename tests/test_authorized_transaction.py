import unittest
from unittest.mock import Mock
from udisks2_authorized_transaction import authorized_transaction
from beta91_experimental_writer import UnsafeTarget

class TransactionSafetyTests(unittest.TestCase):
    def test_confirmation_blocks_before_inspection(self):
        inspect = Mock()
        with self.assertRaises(UnsafeTarget):
            authorized_transaction('image.iso', '/dev/sdb', confirm='ERASE /dev/sdc', inspector=inspect)
        inspect.assert_not_called()

    def test_rejects_non_disk_path(self):
        inspect = Mock()
        with self.assertRaises(ValueError):
            authorized_transaction('image.iso', '/dev/sdb1', confirm='ERASE /dev/sdb1', inspector=inspect)
        inspect.assert_not_called()

    def test_topology_capacity_mismatch_before_staging(self):
        ident = Mock(size_bytes=4096)
        stage = Mock()
        with self.assertRaisesRegex(ValueError, 'Capacity mismatch'):
            authorized_transaction('image.iso','/dev/sdb',confirm='ERASE /dev/sdb',
                inspector=lambda _: ident, validator=lambda *a: True,
                topology=lambda _: {'status':'READ_ONLY_INSPECTED','device':'/dev/sdb','size_bytes':8192},stager=stage)
        stage.assert_not_called()

if __name__ == '__main__': unittest.main()
