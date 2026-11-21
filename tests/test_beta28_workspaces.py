import pathlib,unittest
ROOT=pathlib.Path(__file__).resolve().parents[1]
class Beta28Workspaces(unittest.TestCase):
 def test_qt_network_linked(self):
  s=(ROOT/'CMakeLists.txt').read_text();self.assertIn('Qt6::Network',s)
 def test_read_only_previews(self):
  s=(ROOT/'src/main.cpp').read_text();self.assertIn('READ-ONLY PREVIEW — NO DISK CHANGES',s);self.assertIn('Physical USB operations remain DISABLED',s)
 def test_writer_still_disabled(self):
  s=(ROOT/'system_service.py').read_text();self.assertNotIn('def write_usb(',s)
