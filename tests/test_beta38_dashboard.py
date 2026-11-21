import unittest
from pathlib import Path

SOURCE = (Path(__file__).resolve().parents[1] / "src/main.cpp").read_text()

class Beta38DashboardTests(unittest.TestCase):
    def test_version(self):
        self.assertIn("v1.1.0-beta93", SOURCE)
    def test_status_colors(self):
        self.assertIn("MATCHED  •", SOURCE)
        self.assertIn("WARNING  •", SOURCE)
    def test_writes_disabled(self):
        self.assertIn("Physical writes disabled", SOURCE)
    def test_explicit_baseline(self):
        self.assertIn("Capture new identity baseline (read-only)", SOURCE)
