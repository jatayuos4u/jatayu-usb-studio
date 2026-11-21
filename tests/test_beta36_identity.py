import copy
import json
import unittest
from device_identity_guard import capture_identity, compare_identity


def snap(**overrides):
    disk = {'name': 'sdb', 'path': '/dev/sdb', 'type': 'disk', 'tran': 'usb', 'rm': 1,
            'ro': 0, 'size': 31000000000, 'mountpoints': [None], 'pkname': None,
            'maj:min': '8:16', 'serial': 'ABC123', 'wwn': None, 'model': 'DataTraveler',
            'vendor': 'Kingston', 'children': [
                {'name': 'sdb1', 'path': '/dev/sdb1', 'type': 'part', 'size': 30900000000,
                 'pkname': 'sdb', 'maj:min': '8:17', 'mountpoints': [None]}]}
    disk.update(overrides)
    return json.dumps({'blockdevices': [disk]}).encode()

class IdentityTests(unittest.TestCase):
    def test_capture(self):
        r = capture_identity(snap(), '/dev/sdb'); self.assertTrue(r['ok']); self.assertFalse(r['authorized'])
    def test_compare(self):
        b = capture_identity(snap(), '/dev/sdb'); self.assertTrue(compare_identity(b, snap(), '/dev/sdb')['ok'])
    def test_changed_serial(self):
        b = capture_identity(snap(), '/dev/sdb'); self.assertFalse(compare_identity(b, snap(serial='OTHER'), '/dev/sdb')['ok'])
    def test_changed_size(self):
        b = capture_identity(snap(), '/dev/sdb'); self.assertFalse(compare_identity(b, snap(size=40000000000), '/dev/sdb')['ok'])
    def test_changed_major_minor(self):
        b = capture_identity(snap(), '/dev/sdb'); self.assertFalse(compare_identity(b, snap(**{'maj:min':'8:32'}), '/dev/sdb')['ok'])
    def test_changed_model(self):
        b = capture_identity(snap(), '/dev/sdb'); self.assertFalse(compare_identity(b, snap(model='Other'), '/dev/sdb')['ok'])
    def test_missing_serial(self):
        self.assertFalse(capture_identity(snap(serial=None), '/dev/sdb')['ok'])
    def test_wwn_fallback(self):
        self.assertTrue(capture_identity(snap(serial=None, wwn='wwn123'), '/dev/sdb')['ok'])
    def test_mount_rejected(self):
        self.assertFalse(capture_identity(snap(mountpoints=['/media/usb']), '/dev/sdb')['ok'])
    def test_internal_rejected(self):
        self.assertFalse(capture_identity(snap(tran='sata'), '/dev/sdb')['ok'])
    def test_partition_rejected(self):
        self.assertFalse(capture_identity(snap(), '/dev/sdb1')['ok'])
    def test_bad_baseline(self):
        self.assertFalse(compare_identity({}, snap(), '/dev/sdb')['ok'])
    def test_unplugged(self):
        b = capture_identity(snap(), '/dev/sdb'); self.assertFalse(compare_identity(b, b'{"blockdevices":[]}', '/dev/sdb')['ok'])
    def test_changed_partition(self):
        b = capture_identity(snap(), '/dev/sdb')
        d = json.loads(snap()); d['blockdevices'][0]['children'][0]['size'] -= 1
        self.assertFalse(compare_identity(b, json.dumps(d), '/dev/sdb')['ok'])
    def test_no_writes_ever(self):
        for r in [capture_identity(snap(), '/dev/sdb'), compare_identity(capture_identity(snap(), '/dev/sdb'), snap(), '/dev/sdb')]:
            self.assertFalse(r['writing_enabled']); self.assertFalse(r['authorized'])
    def test_invalid_serial(self):
        self.assertFalse(capture_identity(snap(serial='abc\nxyz'), '/dev/sdb')['ok'])
