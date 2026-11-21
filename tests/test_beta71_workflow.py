import unittest
from pathlib import Path
src=(Path(__file__).resolve().parents[1]/"src/main.cpp").read_text()
class WorkflowTests(unittest.TestCase):
    def test_dark_workflow(self):
        self.assertIn('frame(index==1?"workflow":"light")',src)
        self.assertIn('QFrame#workflow',src)
    def test_advanced_hidden(self):
        self.assertIn('advanced->setVisible(false)',src)
        self.assertIn('advancedToggle->setCheckable(true)',src)
    def test_nonwriting_backend(self):
        self.assertIn('"Capabilities"',src)
        self.assertIn('writing disabled',src)
