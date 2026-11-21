import tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from beta90_write_engine import copy_and_verify,WriteRejected,WriteCancelled

class TestWriteEngine(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name);self.src=self.root/'input.iso';self.src.write_bytes(b'ISO'+b'abc'*3000)
        self.dst=self.root/'output.img'
    def test_verified_copy(self):
        result=copy_and_verify(self.src,self.dst,chunk_size=4096)
        self.assertEqual(self.dst.read_bytes(),self.src.read_bytes())
        self.assertFalse(result['physical_usb_writing'])
        self.assertFalse(result['write_authorized'])
    def test_existing_destination_refused(self):
        self.dst.write_bytes(b'KEEP')
        with self.assertRaises(WriteRejected):copy_and_verify(self.src,self.dst)
        self.assertEqual(self.dst.read_bytes(),b'KEEP')
    def test_symlink_source_refused(self):
        link=self.root/'link.iso';link.symlink_to(self.src)
        with self.assertRaises(WriteRejected):copy_and_verify(link,self.dst)
    def test_symlink_destination_refused(self):
        self.dst.symlink_to(self.src)
        with self.assertRaises(WriteRejected):copy_and_verify(self.src,self.dst)
    def test_directory_source_refused(self):
        with self.assertRaises(WriteRejected):copy_and_verify(self.root,self.dst)
    def test_cancelled(self):
        with self.assertRaises(WriteCancelled):copy_and_verify(self.src,self.dst,cancelled=lambda:True)
    def test_bad_chunk(self):
        with self.assertRaises(WriteRejected):copy_and_verify(self.src,self.dst,chunk_size=2)
    def test_readback_mismatch(self):
        # Corrupt output after write and before readback via progress callback.
        def progress(phase,done,total):
            if phase=='write' and done==total:
                with open(self.dst,'r+b') as f:f.seek(0);f.write(b'BAD')
        with self.assertRaises(WriteRejected):copy_and_verify(self.src,self.dst,chunk_size=4096,progress=progress)
