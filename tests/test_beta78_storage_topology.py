import tempfile
import unittest
from pathlib import Path
from beta64_authorization import Denied
from beta78_storage_topology import inspect_topology, request_write

class TopologyTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        self.block=self.root/'sys/class/block';self.block.mkdir(parents=True)
        self.proc=self.root/'proc/self';self.proc.mkdir(parents=True)
        (self.proc/'mountinfo').write_text('24 23 0:23 / / rw - tmpfs tmpfs rw\n')
        (self.root/'proc/swaps').write_text('Filename Type Size Used Priority\n')
        self.make('sdb','8:16')
    def make(self,name,number):
        p=self.block/name;p.mkdir()
        for key,val in {'dev':number,'size':'1000','removable':'1','ro':'0'}.items(): (p/key).write_text(val)
        for key in ('holders','slaves'): (p/key).mkdir()
        return p
    def scan(self):
        return inspect_topology('/dev/sdb',sys_root=str(self.root/'sys'),proc_root=str(self.root/'proc'))
    def test_clean(self):
        self.assertFalse(self.scan()['writing_enabled'])
    def test_mounted_holder(self):
        self.make('dm-0','253:0');(self.block/'sdb/holders/dm-0').symlink_to(self.block/'dm-0',target_is_directory=True)
        (self.proc/'mountinfo').write_text('24 23 253:0 / / rw - ext4 /dev/dm-0 rw\n')
        with self.assertRaises(Denied):self.scan()
    def test_unmounted_holder_visible(self):
        self.make('dm-0','253:0');(self.block/'sdb/holders/dm-0').symlink_to(self.block/'dm-0',target_is_directory=True)
        self.assertIn('dm-0',self.scan()['dependencies'])
    def test_missing_holders(self):
        (self.block/'sdb/holders').rmdir()
        with self.assertRaises(Denied):self.scan()
    def test_missing_dependency(self):
        (self.block/'sdb/holders/ghost').symlink_to(self.block/'ghost')
        with self.assertRaises(Denied):self.scan()
    def test_cycle(self):
        (self.block/'sdb/holders/sdb').symlink_to(self.block/'sdb',target_is_directory=True)
        with self.assertRaises(Denied):self.scan()
    def test_mounted_partition(self):
        part=self.make('sdb1','8:17');(part/'partition').write_text('1')
        (self.block/'sdb/sdb1').symlink_to(part,target_is_directory=True)
        (self.proc/'mountinfo').write_text('24 23 8:17 / /mnt rw - ext4 /dev/sdb1 rw\n')
        with self.assertRaises(Denied):self.scan()
    def test_no_writes(self):
        with self.assertRaises(Denied):request_write('/dev/sdb')
