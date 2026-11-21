import unittest
from pathlib import Path
src=(Path(__file__).resolve().parents[1]/"src/main.cpp").read_text()
class Beta72WorkflowTests(unittest.TestCase):
    def test_unique_panel_heading(self):
        self.assertIn('txt("USB Image Setup",19,true',src)
        self.assertNotIn('pv->addWidget(txt("Create Bootable USB",21,true))',src)
    def test_accessible_disabled_checkbox(self):
        self.assertIn('QCheckBox:disabled { color:#B8C9E6; }',src)
        self.assertIn('Persistent storage (not available in this preview)',src)
    def test_dark_status_and_sections(self):
        self.assertIn('STEP 3  ·  SAFETY & VERIFICATION',src)
        self.assertIn('"#C4D5F0"',src)
    def test_write_disabled(self):
        self.assertIn('writing remains disabled',src)
        self.assertIn('demoPanel->setVisible(false)',src)
