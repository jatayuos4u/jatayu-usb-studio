import unittest
from pathlib import Path
SOURCE=(Path(__file__).resolve().parents[1]/"src/main.cpp").read_text()
class Beta39DeviceSafetyTests(unittest.TestCase):
    def test_navigation(self):
        self.assertIn('"USB Repair","Device Safety","Settings","About"', SOURCE)
        self.assertIn('i==6?safetyPage():otherPage(i)', SOURCE)
    def test_latched_warning(self):
        self.assertIn('bool baselineInitialized=false;', SOURCE)
        self.assertIn('if(validSnapshot && !baselineInitialized && devices.size()==1)', SOURCE)
        self.assertIn('identityAlert=!matched;', SOURCE)
    def test_read_only(self):
        self.assertIn('Physical writes, cloning, formatting and repair remain disabled.', SOURCE)
        self.assertIn('QMessageBox::Cancel|QMessageBox::Ok', SOURCE)
    def test_layout(self):
        self.assertIn('Banner(){setFixedHeight(166)', SOURCE)
        self.assertIn('card->setMinimumHeight(138)', SOURCE)
