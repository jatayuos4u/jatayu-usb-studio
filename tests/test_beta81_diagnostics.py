import tempfile
import unittest
from pathlib import Path
from beta64_authorization import Denied
from beta78_storage_topology import inspect_topology
from beta79_integrated_inspection import inspect

class TopologyDiagnostics(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.block = self.root / 'sys/class/block'
        self.block.mkdir(parents=True)
        self.proc = self.root / 'proc'
        (self.proc / 'self').mkdir(parents=True)
        (self.proc / 'self/mountinfo').write_text('24 23 0:23 / / rw - tmpfs tmpfs rw\n')
        (self.proc / 'swaps').write_text('Filename Type Size Used Priority\n')
        self.make('sdb','8:16')
    def make(self,name,num):
        p=self.block/name
        p.mkdir()
        for k,v in {'dev':num,'size':'1000','removable':'1','ro':'0'}.items():
            (p/k).write_text(v)
        (p/'holders').mkdir();(p/'slaves').mkdir()
        return p
    def scan(self):
        return inspect_topology('/dev/sdb',sys_root=str(self.root/'sys'),proc_root=str(self.proc))
    def test_clean_simple_usb_is_advisory(self):
        r=self.scan()
        self.assertEqual(r['dependencies'],('sdb',))
        self.assertFalse(r['writing_enabled'])
    def test_missing_holders_identifies_node(self):
        (self.block/'sdb/holders').rmdir()
        with self.assertRaisesRegex(Denied,'Missing holders directory for sdb'):
            self.scan()
    def test_missing_slaves_identifies_node(self):
        (self.block/'sdb/slaves').rmdir()
        with self.assertRaisesRegex(Denied,'Missing slaves directory for sdb'):
            self.scan()
    def test_missing_partition_holders_identifies_partition(self):
        part=self.make('sdb1','8:17')
        (part/'partition').write_text('1')
        (self.block/'sdb/sdb1').symlink_to(part,target_is_directory=True)
        (part/'holders').rmdir()
        with self.assertRaisesRegex(Denied,'Missing holders directory for sdb1'):
            self.scan()
    def test_missing_holder_target_identifies_node(self):
        (self.block/'sdb/holders/dm-0').symlink_to(self.block/'dm-0')
        with self.assertRaisesRegex(Denied,'Missing sysfs block node for dm-0'):
            self.scan()
    def test_mounted_holder_identifies_node(self):
        self.make('dm-0','253:0')
        (self.block/'sdb/holders/dm-0').symlink_to(self.block/'dm-0',target_is_directory=True)
        (self.proc/'self/mountinfo').write_text('24 23 253:0 / / rw - ext4 /dev/dm-0 rw\n')
        with self.assertRaisesRegex(Denied,'Mounted storage dependency: dm-0'):
            self.scan()
    def test_integrated_still_blocks_incomplete_topology(self):
        (self.block/'sdb/slaves').rmdir()
        r=inspect('/dev/sdb',sys_root=str(self.root/'sys'),proc_root=str(self.proc))
        self.assertFalse(r.candidate)
        self.assertFalse(r.writing_enabled)
        self.assertIn('Missing slaves directory for sdb',r.reasons[0])
    def test_write_disabled(self):
        from beta79_integrated_inspection import request_write
        with self.assertRaises(Denied):request_write('/dev/sdb')
