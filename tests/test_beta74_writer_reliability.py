import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from beta73_file_writer import copy_verify, Cancelled

@unittest.skipIf(os.geteuid() == 0, 'Writer deliberately refuses root')
class ReliabilityTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.source = self.base/'source.iso'
        self.source.write_bytes(b'A' * (2 * 1024 * 1024))
        self.out = self.base/'private'
        self.out.mkdir(mode=0o700)

    def test_normal_copy(self):
        self.assertTrue(copy_verify(self.source,self.out,'copy.bin')['verified'])

    def test_mutation_during_progress_fails_and_cleans(self):
        changed = [False]
        def mutate(done, total):
            if not changed[0]:
                changed[0] = True
                with self.source.open('r+b') as f:
                    f.seek(0); f.write(b'B' * 4096)
        with self.assertRaises(ValueError):
            copy_verify(self.source,self.out,'copy.bin',progress=mutate)
        self.assertEqual(list(self.out.iterdir()), [])

    def test_cancel_during_progress_cleans(self):
        flag = [False]
        def progress(done,total): flag[0] = True
        with self.assertRaises(Cancelled):
            copy_verify(self.source,self.out,'copy.bin',progress=progress,cancelled=lambda: flag[0])
        self.assertEqual(list(self.out.iterdir()), [])

    def test_replaced_output_not_deleted_on_failure(self):
        def replace(done,total):
            p = self.out/'copy.bin'
            p.unlink()
            p.write_bytes(b'KEEP')
            raise RuntimeError('interrupted')
        with self.assertRaises(RuntimeError):
            copy_verify(self.source,self.out,'copy.bin',progress=replace)
        self.assertEqual((self.out/'copy.bin').read_bytes(), b'KEEP')

    def test_disk_full_simulation_cleans(self):
        real_write = os.write
        def full(fd, data):
            raise OSError(28, 'No space left on device')
        with patch('beta73_file_writer.os.write', side_effect=full):
            with self.assertRaises(OSError):
                copy_verify(self.source,self.out,'copy.bin')
        self.assertEqual(list(self.out.iterdir()), [])
