"""Prevent stale version labels in the packaged Qt GUI."""
from pathlib import Path
import unittest

class VersionConsistencyTests(unittest.TestCase):
    def test_qt_gui_has_current_version(self):
        source = (Path(__file__).resolve().parents[1] / 'src' / 'main.cpp').read_text()
        self.assertIn('Jatayu USB Studio v1.1.0-beta93', source)
        self.assertNotIn('v1.1.0-beta92', source)

    def test_gui_does_not_claim_physical_writer(self):
        source = (Path(__file__).resolve().parents[1] / 'src' / 'main.cpp').read_text()
        self.assertIn('remains READ-ONLY; no writing is available', source)
