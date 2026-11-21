import unittest
from operation_intent import OperationIntent, preview_intent
from device_revalidation import DeviceFingerprint

F = DeviceFingerprint('/dev/sdb', 8, 16, 100000, '/sys/devices/usb1/block/sdb', 'abc')

class IntentTests(unittest.TestCase):
    def test_correct_identity_still_denies_writes(self):
        r = preview_intent(OperationIntent('write_iso', F, 'ERASE /dev/sdb'), inspector=lambda _: F)
        self.assertTrue(r['ok']); self.assertFalse(r['authorized']); self.assertFalse(r['writing_enabled'])
    def test_confirmation_required(self):
        self.assertFalse(preview_intent(OperationIntent('format_usb', F, ''), inspector=lambda _: F)['ok'])
    def test_wrong_target_confirmation(self):
        self.assertFalse(preview_intent(OperationIntent('repair_usb', F, 'ERASE /dev/sdc'), inspector=lambda _: F)['ok'])
    def test_changed_device_rejected(self):
        changed = DeviceFingerprint('/dev/sdb', 8, 17, 100000, F.sysfs_path, F.serial)
        self.assertFalse(preview_intent(OperationIntent('clone_usb', F, 'ERASE /dev/sdb'), inspector=lambda _: changed)['ok'])
    def test_removed_device_rejected(self):
        def gone(_): raise FileNotFoundError('removed')
        self.assertFalse(preview_intent(OperationIntent('write_iso', F, 'ERASE /dev/sdb'), inspector=gone)['ok'])
    def test_invalid_operation(self):
        self.assertFalse(preview_intent(OperationIntent('execute', F, 'ERASE /dev/sdb'), inspector=lambda _: F)['ok'])
    def test_invalid_payload(self):
        self.assertFalse(preview_intent(None)['ok'])
    def test_repeated_revalidation(self):
        calls=[]
        def inspector(_): calls.append(1); return F
        intent=OperationIntent('write_iso',F,'ERASE /dev/sdb')
        preview_intent(intent,inspector=inspector); preview_intent(intent,inspector=inspector)
        self.assertEqual(len(calls),2)
