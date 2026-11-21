import unittest
from safety_backend import assess

class SafetyTests(unittest.TestCase):
    def setUp(self):
        self.data = {'blockdevices': [
            {'path': '/dev/sda', 'type': 'disk', 'tran': 'sata', 'size': 500000,
             'children': [{'path': '/dev/sda1', 'type': 'part', 'mountpoints': ['/']}]},
            {'path': '/dev/sdb', 'type': 'disk', 'tran': 'usb', 'size': 32000000000,
             'children': [{'path': '/dev/sdb1', 'type': 'part', 'mountpoints': [None]}]}]}
    def test_usb_is_never_authorized(self):
        r = assess(self.data, '/dev/sdb')
        self.assertTrue(r['candidate_checks_passed'])
        self.assertFalse(r['allowed_to_write'])
    def test_system_disk_blocked(self):
        self.assertFalse(assess(self.data, '/dev/sda')['candidate_checks_passed'])
    def test_partition_blocked(self):
        self.assertFalse(assess(self.data, '/dev/sdb1')['candidate_checks_passed'])
    def test_mounted_usb_blocked(self):
        self.data['blockdevices'][1]['children'][0]['mountpoints'] = ['/media/usb']
        self.assertFalse(assess(self.data, '/dev/sdb')['candidate_checks_passed'])
    def test_missing_blocked(self):
        self.assertFalse(assess(self.data, '/dev/sdz')['candidate_checks_passed'])
    def test_bad_path_blocked(self):
        self.assertFalse(assess(self.data, '/dev/../sda')['candidate_checks_passed'])
    def test_swap_blocked(self):
        self.data['blockdevices'][1]['children'][0]['fstype'] = 'swap'
        self.assertFalse(assess(self.data, '/dev/sdb')['candidate_checks_passed'])

if __name__ == '__main__':
    unittest.main()
