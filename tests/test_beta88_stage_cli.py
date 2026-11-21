import contextlib
import io
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from beta88_stage_cli import run

@unittest.skipIf(os.geteuid() == 0, 'Requires non-root account')
class Beta88CliTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        self.iso = self.base/'source.iso'
        self.iso.write_bytes(b'ISO DEMO' * 4000)
        self.output = self.base/'new-private-directory'

    def test_stages_verified_regular_file(self):
        with contextlib.redirect_stdout(io.StringIO()) as out, contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(run(['--iso',str(self.iso),'--output-dir',str(self.output)]),0)
        self.assertEqual((self.output/'staged-image.iso').read_bytes(), self.iso.read_bytes())
        self.assertIn('VERIFIED_FILE_ONLY',out.getvalue())
        self.assertEqual(self.output.stat().st_mode & 0o777,0o700)

    def test_existing_directory_rejected(self):
        self.output.mkdir()
        (self.output/'keep').write_text('untouched')
        with self.assertRaises(SystemExit):
            run(['--iso',str(self.iso),'--output-dir',str(self.output)])
        self.assertEqual((self.output/'keep').read_text(),'untouched')

    def test_symlink_output_rejected(self):
        self.output.symlink_to(self.base, target_is_directory=True)
        with self.assertRaises(SystemExit):
            run(['--iso',str(self.iso),'--output-dir',str(self.output)])

    def test_symlink_input_rejected_and_empty_directory_removed(self):
        link=self.base/'link.iso';link.symlink_to(self.iso)
        with self.assertRaises(OSError):
            run(['--iso',str(link),'--output-dir',str(self.output)])
        self.assertFalse(self.output.exists())

    def test_root_refused(self):
        with patch('beta88_stage_cli.os.geteuid',return_value=0):
            with self.assertRaises(SystemExit):
                run(['--iso',str(self.iso),'--output-dir',str(self.output)])
        self.assertFalse(self.output.exists())
