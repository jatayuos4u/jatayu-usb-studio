import unittest
from pathlib import Path
SOURCE=(Path(__file__).resolve().parents[1]/"src/main.cpp").read_text()
class ExportRegression(unittest.TestCase):
    def test_exclusive_create(self):
        self.assertIn('QIODevice::WriteOnly|QIODevice::NewOnly',SOURCE)
        self.assertIn('QFile file(absolute)',SOURCE)
    def test_no_qsavefile_newonly(self):
        self.assertNotIn('QSaveFile file(path)',SOURCE)
    def test_failure_message(self):
        self.assertIn('Could not create the file:',SOURCE)
        self.assertIn('file.errorString()',SOURCE)
    def test_cleanup(self):
        self.assertIn('QFile::remove(absolute)',SOURCE)
    def test_restricted_paths(self):
        for path in ('/dev/','/proc/','/sys/'):
            self.assertIn('absolute.startsWith("'+path+'")',SOURCE)
    def test_no_overwrite(self):
        self.assertIn('info.exists()',SOURCE)
        self.assertIn('info.isSymLink()',SOURCE)
    def test_readonly_device_policy(self):
        self.assertIn('Physical writes, cloning, formatting and repair remain disabled.',SOURCE)
