import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from beta87_iso_workflow import stage_iso_file, WorkflowError
from beta73_file_writer import Cancelled

@unittest.skipIf(os.geteuid() == 0, 'Non-root file laboratory')
class Beta87WorkflowTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        root = Path(self.temp.name)
        self.iso = root/'input.iso'
        self.iso.write_bytes(b'ISO test data'*10000)
        self.target = root/'private'
        self.target.mkdir(mode=0o700)
        os.chmod(self.target, 0o700)

    def test_complete_file_workflow(self):
        events=[]
        result=stage_iso_file(self.iso, self.target, progress=lambda *x: events.append(x))
        self.assertEqual(result['status'],'VERIFIED_FILE_ONLY')
        self.assertFalse(result['physical_usb_writing'])
        self.assertFalse(result['write_authorized'])
        self.assertEqual((self.target/'staged-image.iso').read_bytes(),self.iso.read_bytes())
        self.assertEqual([x[0] for x in events],['hash','copy','verified'])

    def test_cancellation_before_copy(self):
        with self.assertRaises(Cancelled):
            stage_iso_file(self.iso,self.target,cancelled=lambda: True)
        self.assertEqual(list(self.target.iterdir()),[])

    def test_symlink_input_rejected(self):
        link=self.iso.parent/'link.iso'
        link.symlink_to(self.iso)
        with self.assertRaises(OSError):
            stage_iso_file(link,self.target)

    def test_nonempty_target_rejected(self):
        (self.target/'existing').write_text('keep')
        with self.assertRaises(ValueError):
            stage_iso_file(self.iso,self.target)
        self.assertEqual((self.target/'existing').read_text(),'keep')

    def test_invalid_directory_mode_rejected(self):
        os.chmod(self.target,0o755)
        with self.assertRaises(PermissionError):
            stage_iso_file(self.iso,self.target)

    def test_no_block_device_target(self):
        with self.assertRaises((NotADirectoryError, OSError, PermissionError, ValueError)):
            stage_iso_file(self.iso,'/dev/null')

    def test_hash_mismatch_rejected(self):
        with patch('beta87_iso_workflow.copy_verify',return_value={'sha256':'0'*64,'bytes':len(self.iso.read_bytes()),'verified':True}):
            with self.assertRaises(WorkflowError):
                stage_iso_file(self.iso,self.target)
