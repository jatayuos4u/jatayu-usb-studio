import unittest
from unittest.mock import patch
import beta59_experimental_writer as w
class WriterSafetyTests(unittest.TestCase):
    def test_non_usb_refused(self):
        with self.assertRaises(w.Refused): w.device_info('/tmp/test')
    def test_nested_path_refused(self):
        with self.assertRaises(w.Refused): w.device_info('/dev/disk/by-id/anything')
    def test_invalid_source_refused(self):
        with self.assertRaises(w.Refused): w.write_test('/no-such-file.iso','/dev/sdb','x','',allow_write=True)
    @patch.object(w,'device_info',return_value={'path':'/dev/sdb','bytes':9999999999})
    @patch.object(w,'inspect_iso',return_value={'ok':True,'sha256':'abc','iso_size_bytes':1024})
    def test_default_is_read_only(self,*_):
        self.assertFalse(w.write_test('/tmp/test.iso','/dev/sdb','abc','')['writing_enabled'])
    @patch.object(w,'device_info',return_value={'path':'/dev/sdb','bytes':9999999999})
    @patch.object(w,'inspect_iso',return_value={'ok':True,'sha256':'abc','iso_size_bytes':1024})
    def test_hash_mismatch_refused(self,*_):
        with self.assertRaises(w.Refused): w.write_test('/tmp/test.iso','/dev/sdb','different','')
