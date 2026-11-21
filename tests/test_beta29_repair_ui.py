import pathlib, unittest
ROOT=pathlib.Path(__file__).resolve().parents[1]
class Beta29RepairUITests(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.code=(ROOT/'src/main.cpp').read_text()
    def test_new_page(self): self.assertIn('"USB Repair"',self.code)
    def test_no_download_page(self): self.assertNotIn('ISO Downloads',self.code)
    def test_read_only_diagnostic(self): self.assertIn('READ-ONLY USB DIAGNOSTIC',self.code)
    def test_revalidation(self): self.assertIn('Selected USB device identity changed or disappeared',self.code)
    def test_mount_warning(self): self.assertIn('Mounted partitions:',self.code)
    def test_physical_repair_disabled(self): self.assertIn('Physical USB repair, partitioning and formatting are DISABLED',self.code)
    def test_no_download_manager(self): self.assertNotIn('manager->get(req)',self.code)
