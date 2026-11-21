import sys
import tempfile
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from simulation_backend import simulate

SNAPSHOT = {'blockdevices': [{'name': 'sdb', 'path': '/dev/sdb', 'type': 'disk', 'tran': 'usb',
    'size': 10000, 'mountpoints': [None], 'children': []},
    {'name': 'sda', 'path': '/dev/sda', 'type': 'disk', 'tran': 'sata', 'size': 500000,
     'mountpoints': [None], 'children': [{'name': 'sda1', 'path': '/dev/sda1', 'type': 'part',
     'mountpoints': ['/'], 'fstype': 'ext4'}]}]}

class SimulationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.iso = Path(self.tmp.name) / 'sample.iso'
        self.iso.write_bytes(b'test-only')
    def tearDown(self):
        self.tmp.cleanup()
    def test_safe_candidate_never_authorizes_write(self):
        result = simulate(SNAPSHOT, '/dev/sdb', str(self.iso))
        self.assertTrue(result['simulation_complete'])
        self.assertFalse(result['allowed_to_write'])
    def test_system_disk_blocked(self):
        self.assertFalse(simulate(SNAPSHOT, '/dev/sda', str(self.iso))['simulation_complete'])
    def test_partition_blocked(self):
        self.assertFalse(simulate(SNAPSHOT, '/dev/sda1', str(self.iso))['simulation_complete'])
    def test_missing_iso_blocked(self):
        self.assertFalse(simulate(SNAPSHOT, '/dev/sdb', str(self.iso)+'-missing')['simulation_complete'])
    def test_oversized_iso_blocked(self):
        self.iso.write_bytes(b'x'*10001)
        self.assertFalse(simulate(SNAPSHOT, '/dev/sdb', str(self.iso))['simulation_complete'])
    def test_mounted_usb_blocked(self):
        import copy
        snapshot=copy.deepcopy(SNAPSHOT)
        snapshot['blockdevices'][0]['mountpoints']=['/media/usb']
        self.assertFalse(simulate(snapshot, '/dev/sdb', str(self.iso))['simulation_complete'])

if __name__ == '__main__': unittest.main()
