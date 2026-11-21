import unittest
from unittest.mock import patch
from privileged_writer_contract import DeviceIdentity
from beta91_experimental_writer import write_iso,UnsafeTarget
class TestExperimentalWriter(unittest.TestCase):
    def setUp(self):
        self.ident=DeviceIdentity('/dev/sdb',8,16,'/sys/mock',1024*1024,'usb','serial')
        self.inspect=lambda _:self.ident
        self.validator=lambda *_:True
    def test_default_never_writes(self):
        r=write_iso('/missing.iso','/dev/sdb',inspector=self.inspect,validator=self.validator)
        self.assertFalse(r['writing_enabled'])
    def test_execute_requires_root(self):
        with patch('beta91_experimental_writer.os.geteuid',return_value=1000):
            with self.assertRaises(UnsafeTarget):
                write_iso('/missing.iso','/dev/sdb',execute=True,confirm='ERASE /dev/sdb',inspector=self.inspect,validator=self.validator)
    def test_exact_confirmation_required(self):
        with patch('beta91_experimental_writer.os.geteuid',return_value=0):
            with self.assertRaises(UnsafeTarget):
                write_iso('/missing.iso','/dev/sdb',execute=True,confirm='ERASE /dev/sda',inspector=self.inspect,validator=self.validator)
    def test_validator_rejects(self):
        def deny(*_):raise UnsafeTarget('rejected')
        with self.assertRaises(UnsafeTarget):
            write_iso('/missing.iso','/dev/sdb',inspector=self.inspect,validator=deny)
