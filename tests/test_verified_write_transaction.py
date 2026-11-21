import os
import tempfile
import unittest
from verified_write_transaction import transfer_and_verify
from beta91_experimental_writer import UnsafeTarget, WriteCancelled

class TransactionTests(unittest.TestCase):
    def setUp(self):
        self.src = tempfile.TemporaryFile()
        self.dst = tempfile.TemporaryFile()
        self.src.write(b'abc' * 101)
        self.src.flush()
        self.dst.write(b'X' * 400)
        self.dst.flush()

    def tearDown(self):
        self.src.close()
        self.dst.close()

    def run_tx(self, **kwargs):
        return transfer_and_verify(self.src.fileno(), self.dst.fileno(), 303,
                                   chunk=17, pre_write_check=lambda fd: True, **kwargs)

    def test_round_trip(self):
        phases = []
        result = self.run_tx(progress=lambda p, n, total: phases.append((p,n,total)))
        self.assertEqual(result['bytes'], 303)
        self.assertEqual([p for p,_,_ in phases if p=='verify'][-1], 'verify')
        self.dst.seek(0)
        self.assertEqual(self.dst.read(303), b'abc'*101)

    def test_requires_attestation(self):
        with self.assertRaises(UnsafeTarget):
            transfer_and_verify(self.src.fileno(), self.dst.fileno(), 303)

    def test_rejects_attestation(self):
        with self.assertRaises(UnsafeTarget):
            transfer_and_verify(self.src.fileno(), self.dst.fileno(), 303,
                                pre_write_check=lambda fd: False)
        self.dst.seek(0)
        self.assertEqual(self.dst.read(3), b'XXX')

    def test_cancel_before_write(self):
        with self.assertRaises(WriteCancelled):
            self.run_tx(cancelled=lambda: True)
        self.dst.seek(0)
        self.assertEqual(self.dst.read(3), b'XXX')

    def test_short_source(self):
        with self.assertRaises(UnsafeTarget):
            transfer_and_verify(self.src.fileno(), self.dst.fileno(), 350,
                                pre_write_check=lambda fd: True)

    def test_invalid_size(self):
        with self.assertRaises(UnsafeTarget):
            transfer_and_verify(self.src.fileno(), self.dst.fileno(), 0,
                                pre_write_check=lambda fd: True)

if __name__ == '__main__': unittest.main()
