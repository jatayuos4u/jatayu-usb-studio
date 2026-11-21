import unittest
from pathlib import Path
from tests.test_beta81_diagnostics import TopologyDiagnostics
from beta64_authorization import Denied
from beta79_integrated_inspection import inspect

class PartitionSysfsTests(TopologyDiagnostics):
    def test_partition_missing_optional_slaves_allowed(self):
        part=self.make('sdb1','8:17')
        (part/'partition').write_text('1')
        (self.block/'sdb/sdb1').symlink_to(part,target_is_directory=True)
        (part/'slaves').rmdir()
        report=self.scan()
        self.assertEqual(report['dependencies'],('sdb','sdb1'))
        self.assertFalse(report['writing_enabled'])
        integrated=inspect('/dev/sdb',sys_root=str(self.root/'sys'),proc_root=str(self.proc))
        self.assertTrue(integrated.candidate)
        self.assertFalse(integrated.writing_enabled)
    def test_partition_missing_holders_still_denied(self):
        part=self.make('sdb1','8:17')
        (part/'partition').write_text('1')
        (self.block/'sdb/sdb1').symlink_to(part,target_is_directory=True)
        (part/'holders').rmdir()
        with self.assertRaisesRegex(Denied,'Missing holders directory for sdb1'): self.scan()
    def test_whole_disk_missing_slaves_still_denied(self):
        (self.block/'sdb/slaves').rmdir()
        with self.assertRaisesRegex(Denied,'Missing slaves directory for sdb'): self.scan()
    def test_partition_with_unresolved_holder_denied(self):
        part=self.make('sdb1','8:17')
        (part/'partition').write_text('1')
        (self.block/'sdb/sdb1').symlink_to(part,target_is_directory=True)
        (part/'slaves').rmdir()
        (part/'holders/dm-0').symlink_to(self.block/'dm-0')
        with self.assertRaisesRegex(Denied,'Missing sysfs block node for dm-0'): self.scan()
