import hashlib
import os
import tempfile
import unittest
from beta91_experimental_writer import verify_readback, UnsafeTarget, WriteCancelled

class ReadbackTests(unittest.TestCase):
    def setUp(self):
        self.f=tempfile.TemporaryFile()
        self.payload=b'Jatayu USB Studio test data' * 300
        self.f.write(self.payload); self.f.flush()
        self.hash=hashlib.sha256(self.payload).hexdigest()
    def tearDown(self): self.f.close()
    def test_success(self): self.assertEqual(verify_readback(self.f.fileno(),self.hash,len(self.payload),chunk=67),self.hash)
    def test_corruption_rejected(self):
        with self.assertRaisesRegex(UnsafeTarget,'mismatch'):
            verify_readback(self.f.fileno(),'0'*64,len(self.payload))
    def test_truncation_rejected(self):
        with self.assertRaisesRegex(UnsafeTarget,'truncated'):
            verify_readback(self.f.fileno(),self.hash,len(self.payload)+10)
    def test_cancel_rejected(self):
        with self.assertRaises(WriteCancelled):
            verify_readback(self.f.fileno(),self.hash,len(self.payload),cancelled=lambda: True)
    def test_progress(self):
        progress=[]
        verify_readback(self.f.fileno(),self.hash,len(self.payload),chunk=111,progress=lambda *x:progress.append(x))
        self.assertEqual(progress[-1],('verify',len(self.payload),len(self.payload)))
    def test_zero_size_rejected(self):
        with self.assertRaises(UnsafeTarget):verify_readback(self.f.fileno(),self.hash,0)
    def test_invalid_chunk_rejected(self):
        with self.assertRaises(UnsafeTarget):verify_readback(self.f.fileno(),self.hash,len(self.payload),chunk=0)
