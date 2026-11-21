import unittest
from pathlib import Path

MAIN = (Path(__file__).resolve().parents[1] / "src/main.cpp").read_text()

class Beta32UiContract(unittest.TestCase):
    def test_distinct_destination_filter(self):
        self.assertIn('if(source->itemData(i)==source->currentData())continue;', MAIN)
    def test_single_drive_prompt(self):
        self.assertIn('Connect another USB drive to continue', MAIN)
    def test_no_preview_without_destination(self):
        self.assertIn('preview->setEnabled(false);', MAIN)
        self.assertIn('destination->currentData().toString().isEmpty()', MAIN)
    def test_filesystems(self):
        self.assertIn('fs->addItems({"exFAT","FAT32","NTFS","ext4"})', MAIN)
    def test_writes_still_disabled(self):
        self.assertIn('Physical USB operations remain DISABLED.', MAIN)

if __name__ == '__main__': unittest.main()
