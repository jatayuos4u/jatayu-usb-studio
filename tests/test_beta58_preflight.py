import tempfile
import unittest
from pathlib import Path
from beta58_hardware_preflight import check

class HardwarePreflightTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.iso = Path(self.tmp.name)/'sample.iso'
        self.iso.write_bytes(b'test image')
    def tearDown(self):
        self.tmp.cleanup()
    def test_removable_candidate(self):
        report=check(str(self.iso),'/dev/sdz',inventory_fn=lambda:[dict(path='/dev/sdz',eligible_for_future_hardware_test=True,size_bytes=4096)])
        self.assertTrue(report['ok'])
        self.assertFalse(report['writing_enabled'])
    def test_nonremovable_rejected(self):
        report=check(str(self.iso),'/dev/sda',inventory_fn=lambda:[dict(path='/dev/sda',eligible_for_future_hardware_test=False,size_bytes=4096)])
        self.assertFalse(report['ok'])
    def test_unknown_rejected(self):
        self.assertFalse(check(str(self.iso),'/dev/sdz',inventory_fn=lambda:[])['ok'])
    def test_too_small_rejected(self):
        report=check(str(self.iso),'/dev/sdz',inventory_fn=lambda:[dict(path='/dev/sdz',eligible_for_future_hardware_test=True,size_bytes=2)])
        self.assertFalse(report['ok'])
    def test_invalid_iso_rejected(self):
        self.assertFalse(check('/does/not/exist.iso','/dev/sdz',inventory_fn=lambda:[])['ok'])
