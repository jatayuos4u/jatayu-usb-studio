import unittest
from dataclasses import dataclass
from beta80_inspection_cli import report

@dataclass
class Fake:
    device: str = '/dev/sdb'
    candidate: bool = True
    reasons: tuple = ()
    dependencies: tuple = ('sdb',)
    writing_enabled: bool = False

class TestAdapter(unittest.TestCase):
    def test_advisory(self):
        x=report('/dev/sdb',lambda _:Fake());self.assertEqual(x['status'],'ADVISORY_ONLY');self.assertFalse(x['writing_enabled'])
    def test_denied(self):
        x=report('/dev/sdb',lambda _:Fake(candidate=False,reasons=('mounted',)));self.assertEqual(x['status'],'BLOCKED')
    def test_bad_path(self):self.assertEqual(report('/dev/../sda')['status'],'BLOCKED')
    def test_mismatch(self):self.assertEqual(report('/dev/sdb',lambda _:Fake(device='/dev/sda'))['status'],'BLOCKED')
    def test_write_flag(self):self.assertEqual(report('/dev/sdb',lambda _:Fake(writing_enabled=True))['status'],'BLOCKED')
    def test_exception(self):
        def fail(_):raise OSError('secret')
        self.assertEqual(report('/dev/sdb',fail)['reasons'],['Inspection unavailable'])
    def test_no_reason_denial(self):self.assertEqual(report('/dev/sdb',lambda _:Fake(candidate=False))['status'],'BLOCKED')
