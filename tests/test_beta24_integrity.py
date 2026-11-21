import os
import tempfile
import unittest
from pathlib import Path
from file_backed_writer import copy_image_to_new_file

class Beta24IntegrityTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.src = Path(self.temp.name)/'source.iso'
        self.dst = Path(self.temp.name)/'result.img'
        self.src.write_bytes(b'A'*8192)

    def test_success(self):
        result = copy_image_to_new_file(str(self.src), str(self.dst))
        self.assertTrue(result['verified'])

    def test_source_changed_during_verify(self):
        def status(event):
            if event['phase'] == 'verify':
                self.src.write_bytes(b'B'*8192)
        with self.assertRaises(OSError):
            copy_image_to_new_file(str(self.src), str(self.dst), status=status)
        self.assertFalse(self.dst.exists())

    def test_same_size_source_changed_with_preserved_timestamp(self):
        initial = self.src.stat()
        def status(event):
            if event['phase'] == 'verify':
                self.src.write_bytes(b'B' * 8192)
                os.utime(self.src, ns=(initial.st_atime_ns, initial.st_mtime_ns))
        with self.assertRaises(OSError):
            copy_image_to_new_file(str(self.src), str(self.dst), status=status)
        self.assertFalse(self.dst.exists())

    def test_destination_replaced_during_verify(self):
        replacement = Path(self.temp.name)/'replacement'
        replacement.write_bytes(b'R'*8192)
        def status(event):
            if event['phase'] == 'verify':
                os.replace(replacement, self.dst)
        with self.assertRaises(OSError):
            copy_image_to_new_file(str(self.src), str(self.dst), status=status)
        self.assertEqual(self.dst.read_bytes(), b'R'*8192)

    def test_corrupted_output_detected(self):
        def status(event):
            if event['phase'] == 'copy':
                self.dst.write_bytes(b'Z'*8192)
        with self.assertRaises(OSError):
            copy_image_to_new_file(str(self.src), str(self.dst), status=status)
        self.assertFalse(self.dst.exists())

    def test_source_removed_during_verify(self):
        def status(event):
            if event['phase'] == 'verify':
                self.src.unlink()
        with self.assertRaises(OSError):
            copy_image_to_new_file(str(self.src), str(self.dst), status=status)
        self.assertFalse(self.dst.exists())

    def test_service_remains_nonwriting(self):
        import system_service
        self.assertNotIn('WriteImage', Path(system_service.__file__).read_text())
