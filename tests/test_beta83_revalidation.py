import unittest
from dataclasses import replace
from beta79_integrated_inspection import InspectionReport
from beta83_inspection_cli import report, request_write

GOOD = InspectionReport('/dev/sdb', True, (), ('sdb', 'sdb1'))

class RevalidationTests(unittest.TestCase):
    def test_clean_advisory(self):
        x = report('/dev/sdb', lambda _: GOOD)
        self.assertEqual(x['status'], 'ADVISORY_ONLY')
        self.assertFalse(x['writing_enabled'])
    def test_two_passes(self):
        calls=[]
        def f(d): calls.append(d); return GOOD
        report('/dev/sdb',f)
        self.assertEqual(calls,['/dev/sdb','/dev/sdb'])
    def test_changed_dependencies(self):
        vals=iter([GOOD,replace(GOOD,dependencies=('sdb','sdb2'))])
        self.assertEqual(report('/dev/sdb',lambda _: next(vals))['status'],'BLOCKED')
    def test_changed_candidate(self):
        vals=iter([GOOD,replace(GOOD,candidate=False,reasons=('Mounted',))])
        self.assertFalse(report('/dev/sdb',lambda _: next(vals))['candidate'])
    def test_mismatch_path(self):
        self.assertFalse(report('/dev/sdb',lambda _: replace(GOOD,device='/dev/sda'))['candidate'])
    def test_unexpected_authorization(self):
        self.assertFalse(report('/dev/sdb',lambda _: replace(GOOD,writing_enabled=True))['candidate'])
    def test_empty_dependencies(self):
        self.assertFalse(report('/dev/sdb',lambda _: replace(GOOD,dependencies=()))['candidate'])
    def test_rejection_reason(self):
        x=report('/dev/sdb',lambda _: replace(GOOD,candidate=False,reasons=('Mounted',)))
        self.assertEqual(x['reasons'],['Mounted'])
    def test_missing_reason(self):
        self.assertFalse(report('/dev/sdb',lambda _: replace(GOOD,candidate=False))['candidate'])
    def test_collector_error(self):
        def fail(_): raise OSError('disconnected')
        self.assertFalse(report('/dev/sdb',fail)['candidate'])
    def test_invalid_path(self):
        self.assertFalse(report('/dev/sdb1/../../sda',lambda _: GOOD)['candidate'])
    def test_write_disabled(self):
        with self.assertRaises(PermissionError): request_write()
