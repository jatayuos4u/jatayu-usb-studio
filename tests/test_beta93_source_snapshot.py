import hashlib
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from beta91_experimental_writer import stage_iso_verified, UnsafeTarget, WriteCancelled

class SnapshotTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.iso=Path(self.temp.name)/'image.iso'
        self.data=b'Jatayu USB Studio'*4096
        self.iso.write_bytes(self.data)
    def tearDown(self): self.temp.cleanup()
    def test_snapshot_digest_and_length(self):
        with_snapshot, digest, size=stage_iso_verified(str(self.iso),max_bytes=len(self.data),chunk=117)
        with with_snapshot as f:
            self.assertEqual(f.read(),self.data)
        self.assertEqual(size,len(self.data))
        self.assertEqual(digest,hashlib.sha256(self.data).hexdigest())
    def test_source_replacement_does_not_change_snapshot(self):
        f, digest, size=stage_iso_verified(str(self.iso),max_bytes=len(self.data))
        self.iso.write_bytes(b'Z'*len(self.data))
        with f:self.assertEqual(f.read(),self.data)
    def test_oversized_rejected(self):
        with self.assertRaises(UnsafeTarget):stage_iso_verified(str(self.iso),max_bytes=len(self.data)-1)
    def test_symlink_rejected(self):
        link=Path(self.temp.name)/'link.iso';link.symlink_to(self.iso)
        with self.assertRaises(OSError):stage_iso_verified(str(link),max_bytes=len(self.data))
    def test_cancelled(self):
        with self.assertRaises(WriteCancelled):stage_iso_verified(str(self.iso),max_bytes=len(self.data),cancelled=lambda:True)
    def test_bad_chunk(self):
        with self.assertRaises(UnsafeTarget):stage_iso_verified(str(self.iso),max_bytes=len(self.data),chunk=0)
    def test_empty(self):
        self.iso.write_bytes(b'')
        with self.assertRaises(UnsafeTarget):stage_iso_verified(str(self.iso),max_bytes=100)
