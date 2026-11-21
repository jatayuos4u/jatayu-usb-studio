import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]

class TestGuiContract(unittest.TestCase):
    def test_warning_latched(self):
        source = (ROOT / 'src/main.cpp').read_text()
        self.assertIn('identityAlert=!matched;', source)
        self.assertIn('baselineRequested=true;refreshDrives();', source)
    def test_no_write_authorization(self):
        source = (ROOT / 'src/main.cpp').read_text()
        self.assertIn('No writes enabled.', source)
        self.assertIn('NO — disabled', source)
    def test_partition_fingerprint(self):
        source = (ROOT / 'src/main.cpp').read_text()
        self.assertIn('guiFingerprint', source)
        self.assertIn('parts.sort()', source)
