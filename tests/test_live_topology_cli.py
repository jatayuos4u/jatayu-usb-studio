import json
import subprocess
import unittest
from types import SimpleNamespace
from unittest.mock import patch
from live_topology_cli import inspect_live, LSBLK_COLUMNS

DISK = {"path": "/dev/sdb", "type": "disk", "tran": "usb", "rm": 1, "ro": 0,
        "size": 31000000000, "mountpoints": [None], "pkname": None,
        "children": [{"path": "/dev/sdb1", "type": "part", "mountpoints": [None]}]}

def runner_for(disk):
    def runner(args, **kw):
        assert args == ['lsblk', '--json', '--bytes', '--output', LSBLK_COLUMNS]
        assert kw['timeout'] == 8 and kw['capture_output']
        return SimpleNamespace(returncode=0, stdout=json.dumps({'blockdevices':[disk]}).encode())
    return runner

class LiveTopologyTests(unittest.TestCase):
    def test_safe_advisory(self):
        result=inspect_live('/dev/sdb',runner=runner_for(DISK))
        self.assertTrue(result['ok']);self.assertFalse(result['authorized']);self.assertFalse(result['writing_enabled'])
        self.assertEqual(result['partition_count'],1)
    def test_mount_blocks(self):
        disk={**DISK,'mountpoints':['/mnt/test']}
        self.assertFalse(inspect_live('/dev/sdb',runner=runner_for(disk))['ok'])
    def test_internal_blocks(self):
        disk={**DISK,'tran':'sata'}
        self.assertFalse(inspect_live('/dev/sdb',runner=runner_for(disk))['ok'])
    def test_nonremovable_blocks(self):
        disk={**DISK,'rm':0}
        self.assertFalse(inspect_live('/dev/sdb',runner=runner_for(disk))['ok'])
    def test_readonly_blocks(self):
        disk={**DISK,'ro':1}
        self.assertFalse(inspect_live('/dev/sdb',runner=runner_for(disk))['ok'])
    def test_partition_target_blocks(self):
        self.assertFalse(inspect_live('/dev/sdb1',runner=runner_for(DISK))['ok'])
    def test_missing_target_blocks(self):
        self.assertFalse(inspect_live('/dev/sdc',runner=runner_for(DISK))['ok'])
    def test_invalid_path_never_invokes_runner(self):
        def bad(*a,**k):raise AssertionError('should not invoke')
        self.assertFalse(inspect_live('/dev/../sda',runner=bad)['ok'])
    def test_lsblk_error_blocks(self):
        def bad(*a,**k):return SimpleNamespace(returncode=1,stdout=b'')
        self.assertFalse(inspect_live('/dev/sdb',runner=bad)['ok'])
    def test_timeout_blocks(self):
        def bad(*a,**k):raise subprocess.TimeoutExpired('lsblk',8)
        self.assertFalse(inspect_live('/dev/sdb',runner=bad)['ok'])
    def test_invalid_json_blocks(self):
        def bad(*a,**k):return SimpleNamespace(returncode=0,stdout=b'{')
        self.assertFalse(inspect_live('/dev/sdb',runner=bad)['ok'])
    def test_oversized_output_blocks(self):
        def bad(*a,**k):return SimpleNamespace(returncode=0,stdout=b'x'*1048577)
        self.assertFalse(inspect_live('/dev/sdb',runner=bad)['ok'])
    def test_missing_mount_state_blocks(self):
        disk={**DISK};disk.pop('mountpoints')
        self.assertFalse(inspect_live('/dev/sdb',runner=runner_for(disk))['ok'])
    def test_symlinked_child_complex_blocks(self):
        disk={**DISK,'children':[{'path':'/dev/dm-0','type':'crypt','mountpoints':[None]}]}
        self.assertFalse(inspect_live('/dev/sdb',runner=runner_for(disk))['ok'])
