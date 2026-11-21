import tempfile
import unittest
from pathlib import Path
from live_safety import _devnums, inspect_iso, SafetyFailure

class LiveSafetyTests(unittest.TestCase):
    def test_mountinfo(self):
        self.assertEqual(_devnums('42 1 8:17 / /media/usb rw - ext4 /dev/sdb1 rw'), {(8,17)})
    def test_bad_mountinfo_fails_closed(self):
        with self.assertRaises(SafetyFailure): _devnums('bad')
    def test_hash_never_authorizes(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'test.iso';p.write_bytes(b'ISO test content')
            report=inspect_iso(str(p))
            self.assertFalse(report['writing_authorized'])
            self.assertFalse(report['checksum_verified'])
            self.assertTrue(inspect_iso(str(p),expected_sha256=report['sha256'])['checksum_verified'])
            with self.assertRaises(SafetyFailure): inspect_iso(str(p),expected_sha256='0'*64)
    def test_empty_iso_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'empty.iso';p.touch()
            with self.assertRaises(SafetyFailure): inspect_iso(str(p))
    def test_missing_iso_rejected(self):
        with self.assertRaises(SafetyFailure): inspect_iso('/missing/example.iso')
