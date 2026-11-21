"""Regression guards for GUI's fail-closed completion handling."""
import unittest
from pathlib import Path

SOURCE = (Path(__file__).resolve().parents[1] / 'src/main.cpp').read_text()

class GuiVerifiedCompletionContract(unittest.TestCase):
    def test_success_requires_verified_result(self):
        self.assertIn('obj.value("status").toString()=="WRITTEN_AND_VERIFIED"', SOURCE)
        self.assertIn('code!=0 || !*verifiedResult', SOURCE)
        self.assertIn('obj.value("sha256").toString()', SOURCE)

    def test_progress_only_full_after_verification(self):
        self.assertIn('*verifiedResult=true;', SOURCE)
        self.assertIn('writeProgress->setValue(100);', SOURCE)
        self.assertIn('Unexpected writer result; verification not confirmed.', SOURCE)

if __name__ == '__main__':
    unittest.main()
