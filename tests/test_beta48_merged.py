import hashlib
import os
from pathlib import Path
import tempfile
import unittest
from iso_write_preflight import inspect_iso
from usb_write_contract import ProposedWriteRequest, prepare_write, execute_write

class Beta48Tests(unittest.TestCase):
    def test_regular_iso(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d)/'test.iso'; p.write_bytes(b'fake iso test data')
            r = inspect_iso(str(p))
            self.assertTrue(r['ok']); self.assertFalse(r['writing_enabled'])
            self.assertEqual(r['sha256'], hashlib.sha256(b'fake iso test data').hexdigest())
    def test_matching_digest(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'test.iso';p.write_bytes(b'data')
            self.assertTrue(inspect_iso(str(p),hashlib.sha256(b'data').hexdigest())['ok'])
    def test_mismatched_digest(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'test.iso';p.write_bytes(b'data')
            self.assertFalse(inspect_iso(str(p),'0'*64)['ok'])
    def test_symlink_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'a.iso';p.write_bytes(b'data')
            q=Path(d)/'b.iso';q.symlink_to(p)
            self.assertFalse(inspect_iso(str(q))['ok'])
    def test_directory_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertFalse(inspect_iso(str(Path(d)/'x.iso'))['ok'])
    def test_device_rejected(self):
        self.assertFalse(inspect_iso('/dev/sdb')['ok'])
    def test_empty_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'empty.iso';p.touch()
            self.assertFalse(inspect_iso(str(p))['ok'])
    def test_invalid_digest_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'test.iso';p.write_bytes(b'data')
            self.assertFalse(inspect_iso(str(p),'bad')['ok'])
    def test_contract_never_authorizes(self):
        req=ProposedWriteRequest('0'*64,'/dev/sdb','SERIAL','8:16',12345)
        for f in (prepare_write,execute_write):
            for caller in (None,{'uid':0}):
                r=f(req,caller=caller,polkit=True)
                self.assertFalse(r['authorized']);self.assertFalse(r['writing_enabled'])
