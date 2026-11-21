import unittest
from device_revalidation import DeviceFingerprint, DeviceRejected, compare_fingerprints, check_live
from privileged_service import PrivilegedWriterBoundary
import json

F = DeviceFingerprint('/dev/sdb', 8, 16, 31000000000, '/sys/devices/usb1/1-1/block/sdb', 'USB-123')

def request(**overrides):
    data = dict(version=2, target=F.path, iso_path='/tmp/example.iso',
                expected_major=F.major, expected_minor=F.minor, expected_size=F.size_bytes,
                expected_sysfs_path=F.sysfs_path, expected_serial=F.serial)
    data.update(overrides)
    return json.dumps(data).encode()

class RevalidationTests(unittest.TestCase):
    def test_matching_identity_never_authorizes(self):
        self.assertEqual(check_live(F, inspector=lambda p: F)['writing_authorized'], False)
    def test_replaced_device_rejected(self):
        self.assertFalse(check_live(F, inspector=lambda p: DeviceFingerprint(F.path, F.major, F.minor, F.size_bytes, F.sysfs_path, 'changed'))['ok'])
    def test_capacity_changed_rejected(self):
        self.assertFalse(check_live(F, inspector=lambda p: DeviceFingerprint(F.path,8,16,1,F.sysfs_path,F.serial))['ok'])
    def test_device_missing_rejected(self):
        def missing(p): raise FileNotFoundError(p)
        self.assertFalse(check_live(F, inspector=missing)['ok'])
    def test_invalid_fingerprint_rejected(self):
        with self.assertRaises(DeviceRejected): compare_fingerprints(F, {})
    def test_service_prepare_read_only(self):
        result = PrivilegedWriterBoundary(inspector=lambda p: F).prepare(request())
        self.assertTrue(result['ok']); self.assertFalse(result['authorized'])
    def test_service_changed_target_rejected(self):
        result = PrivilegedWriterBoundary(inspector=lambda p: F).prepare(request(expected_minor=17))
        self.assertFalse(result['ok']); self.assertFalse(result['authorized'])
    def test_service_rejects_malformed_request(self):
        self.assertFalse(PrivilegedWriterBoundary().prepare(b'not-json')['authorized'])
    def test_service_write_always_denied(self):
        self.assertFalse(PrivilegedWriterBoundary().write(request())['authorized'])
    def test_service_has_no_polkit(self):
        caps = PrivilegedWriterBoundary().capabilities()
        self.assertFalse(caps['polkit_enabled']); self.assertFalse(caps['writing_enabled'])
