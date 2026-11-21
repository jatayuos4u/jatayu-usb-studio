import pathlib,unittest
ROOT=pathlib.Path(__file__).resolve().parents[1]
class Beta26GUI(unittest.TestCase):
    def test_version(self):
        s=(ROOT/'src/main.cpp').read_text()
        self.assertIn('Jatayu USB Studio v1.1.0-beta93',s)
        self.assertNotIn('Beta 21 remains READ-ONLY',s)
    def test_distinct_progress_bars(self):
        s=(ROOT/'src/main.cpp').read_text()
        self.assertIn('Verifying SHA-256 · 0%',s)
        self.assertIn('verifyProgress->setValue(pct)',s)
        self.assertIn('demoProgress->setValue(pct)',s)
    def test_cancel_not_failure(self):
        s=(ROOT/'src/main.cpp').read_text()
        self.assertIn('obj.value("cancelled").toBool()',s)
        self.assertIn('Cancelled — file copy stopped',s)
    def test_result_required(self):
        s=(ROOT/'src/main.cpp').read_text()
        self.assertIn('resultReceived',s)
        self.assertIn('Interrupted — no final result received',s)
    def test_bridge_still_file_only(self):
        s=(ROOT/'file_copy_demo_cli.py').read_text()
        self.assertIn('copy_image_to_new_file',s)
        self.assertNotIn('os.open("/dev/',s)
