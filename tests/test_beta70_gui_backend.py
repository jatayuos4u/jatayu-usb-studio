import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
class BackendGuiTest(unittest.TestCase):
    def test_gui_uses_read_only_busctl(self):
        text=(ROOT/'src/main.cpp').read_text()
        self.assertIn('"Capabilities"',text)
        self.assertIn('"--system","--timeout=3s","call"',text)
        self.assertIn('"inspection_only"',text)
        self.assertIn('backendTimer.start(5000)',text)
    def test_gui_rejects_unverified_service(self):
        text=(ROOT/'src/main.cpp').read_text()
        self.assertIn('Backend: unavailable / unverified',text)
        self.assertIn('obj.value("writing_enabled").isBool()',text)
        self.assertIn('obj.value("authorized").isBool()',text)
