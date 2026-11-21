import unittest
from pathlib import Path

SRC=Path(__file__).resolve().parents[1]/"src/main.cpp"
class Beta42Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.code=SRC.read_text()
    def test_export_exclusive(self): self.assertIn("QFile file(absolute)",self.code); self.assertIn("QIODevice::NewOnly",self.code)
    def test_export_no_overwrite(self): self.assertIn("info.exists()",self.code)
    def test_export_no_symlink(self): self.assertIn("info.isSymLink()",self.code)
    def test_export_no_device(self): self.assertIn('absolute.startsWith("/dev/")',self.code)
    def test_multi_device_baseline(self): self.assertIn('devices.size()==1',self.code)
    def test_inspection_failure(self): self.assertIn('lsblk inspection failed',self.code)
    def test_event_filter(self): self.assertIn('"Critical","critical"',self.code)
    def test_no_physical_writer(self): self.assertIn('Physical writes, cloning, formatting and repair remain disabled.',self.code)
