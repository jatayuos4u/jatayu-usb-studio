import hashlib
import os
from pathlib import Path
import tempfile
import unittest
from file_backed_writer import copy_image_to_new_file, CopyCancelled, UnsafeDestination

class Beta22FileWriterTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.src = self.root / 'image.iso'
        self.src.write_bytes(b'JatayuOS image test\x00' * 10000)
        self.dst = self.root / 'result.img'

    def test_success_and_hash(self):
        r = copy_image_to_new_file(str(self.src), str(self.dst))
        self.assertEqual(self.dst.read_bytes(), self.src.read_bytes())
        self.assertEqual(r['sha256'], hashlib.sha256(self.src.read_bytes()).hexdigest())
        self.assertTrue(r['verified'])

    def test_progress(self):
        events=[]
        copy_image_to_new_file(str(self.src), str(self.dst), progress=lambda n,t: events.append((n,t)))
        self.assertEqual(events[-1], (self.src.stat().st_size, self.src.stat().st_size))

    def test_cancel_before_start(self):
        with self.assertRaises(CopyCancelled):
            copy_image_to_new_file(str(self.src), str(self.dst), cancelled=lambda: True)
        self.assertFalse(self.dst.exists())

    def test_cancel_during_copy_cleans(self):
        with self.assertRaises(CopyCancelled):
            copy_image_to_new_file(str(self.src), str(self.dst), cancelled=lambda: self.dst.exists() and self.dst.stat().st_size > 0)
        self.assertFalse(self.dst.exists())

    def test_existing_destination_untouched(self):
        self.dst.write_bytes(b'KEEP')
        with self.assertRaises(FileExistsError):
            copy_image_to_new_file(str(self.src), str(self.dst))
        self.assertEqual(self.dst.read_bytes(), b'KEEP')

    def test_destination_symlink_rejected(self):
        other = self.root / 'other'; other.write_bytes(b'KEEP')
        self.dst.symlink_to(other)
        with self.assertRaises(FileExistsError):
            copy_image_to_new_file(str(self.src), str(self.dst))
        self.assertEqual(other.read_bytes(), b'KEEP')

    def test_source_symlink_rejected(self):
        link = self.root / 'link'; link.symlink_to(self.src)
        with self.assertRaises(OSError):
            copy_image_to_new_file(str(link), str(self.dst))
        self.assertFalse(self.dst.exists())

    def test_empty_source_rejected(self):
        self.src.write_bytes(b'')
        with self.assertRaises(ValueError):
            copy_image_to_new_file(str(self.src), str(self.dst))

    def test_directory_source_rejected(self):
        with self.assertRaises((ValueError, OSError)):
            copy_image_to_new_file(str(self.root), str(self.dst))

    def test_relative_destination_rejected(self):
        with self.assertRaises(ValueError):
            copy_image_to_new_file(str(self.src), 'result.img')

    def test_failure_callback_removes_partial(self):
        def fail(n,t):
            raise RuntimeError('simulate crash')
        with self.assertRaises(RuntimeError):
            copy_image_to_new_file(str(self.src), str(self.dst), progress=fail)
        self.assertFalse(self.dst.exists())

    def test_service_still_nonwriting(self):
        import system_service
        self.assertFalse(system_service.capabilities()['writing_enabled'])
