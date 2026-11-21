import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from beta73_file_writer import copy_verify, Cancelled

class FileWriterTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        self.src = self.base/'source.iso'
        self.src.write_bytes(b'JATAYU' * 100000)
        self.dest = self.base/'output'
        self.dest.mkdir(mode=0o700)

    def run_copy(self, *args, **kwargs):
        return copy_verify(*args, **kwargs)

    @unittest.skipIf(os.geteuid() == 0, 'Regular-file writer refuses root')
    def test_regular_file_copy_and_hash(self):
        result = self.run_copy(self.src, self.dest, 'image.bin')
        self.assertTrue(result['verified'])
        self.assertFalse(result['physical_usb_writing'])
        self.assertEqual((self.dest/'image.bin').read_bytes(), self.src.read_bytes())

    @unittest.skipIf(os.geteuid() == 0, 'Regular-file writer refuses root')
    def test_cancel_cleans_partial(self):
        with self.assertRaises(Cancelled):
            self.run_copy(self.src, self.dest, 'image.bin', cancelled=lambda: True)
        self.assertEqual(list(self.dest.iterdir()), [])

    @unittest.skipIf(os.geteuid() == 0, 'Regular-file writer refuses root')
    def test_reject_existing_output(self):
        (self.dest/'image.bin').write_bytes(b'keep')
        with self.assertRaises(ValueError):
            self.run_copy(self.src, self.dest, 'image.bin')
        self.assertEqual((self.dest/'image.bin').read_bytes(), b'keep')

    @unittest.skipIf(os.geteuid() == 0, 'Regular-file writer refuses root')
    def test_reject_directory_traversal(self):
        with self.assertRaises(ValueError):
            self.run_copy(self.src, self.dest, '../bad')

    @unittest.skipIf(os.geteuid() == 0, 'Regular-file writer refuses root')
    def test_reject_symlink_source(self):
        link = self.base/'link.iso'
        link.symlink_to(self.src)
        with self.assertRaises(OSError):
            self.run_copy(link, self.dest, 'image.bin')

    @unittest.skipIf(os.geteuid() == 0, 'Regular-file writer refuses root')
    def test_reject_world_readable_directory(self):
        self.dest.chmod(0o755)
        with self.assertRaises(PermissionError):
            self.run_copy(self.src, self.dest, 'image.bin')

    def test_refuse_root(self):
        with patch('beta73_file_writer.os.geteuid', return_value=0):
            with self.assertRaises(PermissionError):
                copy_verify(self.src, self.dest, 'image.bin')

    @unittest.skipIf(os.geteuid() == 0, 'Regular-file writer refuses root')
    def test_progress(self):
        updates = []
        self.run_copy(self.src, self.dest, 'image.bin', progress=lambda done, total: updates.append((done,total)))
        self.assertEqual(updates[-1], (self.src.stat().st_size,self.src.stat().st_size))

if __name__ == '__main__': unittest.main()
