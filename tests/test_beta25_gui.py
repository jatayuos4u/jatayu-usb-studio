import pathlib
import unittest
ROOT=pathlib.Path(__file__).resolve().parents[1]
class Beta25GUI(unittest.TestCase):
    def test_gui_has_safe_panel(self):
        s=(ROOT/'src/main.cpp').read_text()
        self.assertIn('File-backed progress laboratory',s)
        self.assertIn('file_copy_demo_cli.py',s)
        self.assertIn('Cancel file copy',s)
    def test_no_usb_writer_in_bridge(self):
        s=(ROOT/'file_copy_demo_cli.py').read_text()
        self.assertIn('copy_image_to_new_file',s)
        self.assertNotIn('os.open("/dev/',s)
    def test_bridge_installed(self):
        self.assertIn('file_copy_demo_cli.py DESTINATION', (ROOT/'CMakeLists.txt').read_text())
