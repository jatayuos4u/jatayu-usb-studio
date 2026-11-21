import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from file_backed_writer import copy_image_to_new_file, CopyCancelled

class Beta23ReliabilityTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.src = self.root / 'source.iso'
        self.dst = self.root / 'output.img'
        self.src.write_bytes(os.urandom(2 * 1024 * 1024 + 37))

    def test_phases_and_totals(self):
        events=[]
        copy_image_to_new_file(self.src,self.dst,status=events.append)
        self.assertEqual(events[-1]['phase'],'complete')
        self.assertEqual({e['phase'] for e in events},{'copy','verify','complete'})
        for phase in ('copy','verify'):
            samples=[e for e in events if e['phase']==phase]
            self.assertEqual(samples[-1]['bytes_done'],self.src.stat().st_size)
            self.assertEqual([e['bytes_done'] for e in samples], sorted(e['bytes_done'] for e in samples))

    def test_speed_nonnegative(self):
        events=[]
        ticks=iter([1.0]+[2.0]*30)
        copy_image_to_new_file(self.src,self.dst,status=events.append,clock=lambda:next(ticks))
        self.assertTrue(all(e['bytes_per_second']>=0 for e in events))

    def test_zero_elapsed_safe(self):
        events=[]
        copy_image_to_new_file(self.src,self.dst,status=events.append,clock=lambda:10.0)
        self.assertTrue(all(e['bytes_per_second']==0 for e in events))

    def test_cancel_during_verification_removes_output(self):
        phase=['copy']
        def status(e): phase[0]=e['phase']
        def cancelled(): return phase[0]=='verify'
        with self.assertRaises(CopyCancelled):
            copy_image_to_new_file(self.src,self.dst,status=status,cancelled=cancelled)
        self.assertFalse(self.dst.exists())

    def test_status_exception_removes_partial(self):
        def fail(e): raise RuntimeError('progress sink failure')
        with self.assertRaises(RuntimeError):
            copy_image_to_new_file(self.src,self.dst,status=fail)
        self.assertFalse(self.dst.exists())

    def test_verify_status_exception_removes_output(self):
        def fail(e):
            if e['phase']=='verify': raise RuntimeError('verification observer failure')
        with self.assertRaises(RuntimeError):
            copy_image_to_new_file(self.src,self.dst,status=fail)
        self.assertFalse(self.dst.exists())

    def test_truncated_readback_detected(self):
        def corrupt(e):
            if e['phase']=='verify' and e['bytes_done']>0:
                with open(self.dst,'r+b') as f: f.truncate(1)
        with self.assertRaises(IOError):
            copy_image_to_new_file(self.src,self.dst,status=corrupt)
        self.assertFalse(self.dst.exists())

    def test_destination_exists_untouched(self):
        self.dst.write_bytes(b'KEEP')
        with self.assertRaises(FileExistsError):
            copy_image_to_new_file(self.src,self.dst,status=lambda e:None)
        self.assertEqual(self.dst.read_bytes(),b'KEEP')

    def test_no_service_write_capability(self):
        import system_service
        self.assertFalse(system_service.capabilities()['writing_enabled'])

    def test_no_block_device_write(self):
        import inspect, system_service
        self.assertNotIn('WriteImage',inspect.getsource(system_service))
