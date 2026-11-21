import os
import stat
import unittest
from types import SimpleNamespace
from beta91_experimental_writer import reject_active_swap, UnsafeTarget

HEADER = 'Filename\tType\tSize\tUsed\tPriority\n'

def fake_stat(path):
    if path == '/dev/sdb2':
        return SimpleNamespace(st_mode=stat.S_IFBLK | 0o600, st_rdev=os.makedev(8, 18))
    return SimpleNamespace(st_mode=stat.S_IFBLK | 0o600, st_rdev=os.makedev(8, 1))

class ActiveSwapGuardTests(unittest.TestCase):
    def test_active_partition_swap_rejected(self):
        with self.assertRaisesRegex(UnsafeTarget, 'active swap'):
            reject_active_swap({(8, 16), (8, 18)}, swaps_text=HEADER+'/dev/sdb2 partition 1000 0 -2\n', stat_device=fake_stat)

    def test_unrelated_swap_accepted(self):
        reject_active_swap({(8, 16), (8, 18)}, swaps_text=HEADER+'/dev/sda1 partition 1000 0 -2\n', stat_device=fake_stat)

    def test_unreadable_swap_device_fails_closed(self):
        def missing(_): raise FileNotFoundError()
        with self.assertRaisesRegex(UnsafeTarget, 'Cannot identify'):
            reject_active_swap({(8, 16)}, swaps_text=HEADER+'/dev/sdb2 partition 1000 0 -2\n', stat_device=missing)

    def test_malformed_swap_info_fails_closed(self):
        with self.assertRaises(UnsafeTarget):
            reject_active_swap({(8, 16)}, swaps_text='broken', stat_device=fake_stat)

if __name__ == '__main__': unittest.main()
