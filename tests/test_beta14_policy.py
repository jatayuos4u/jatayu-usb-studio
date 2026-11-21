import unittest
from pathlib import Path
from privileged_writer_policy import evaluate_write_request, WriterCapability

ROOT = Path(__file__).resolve().parents[1]
class Beta14PolicyTests(unittest.TestCase):
    def test_all_true_still_denied(self):
        r = evaluate_write_request(**{k: True for k in ('caller_authenticated','polkit_authorized','device_identity_current','device_exclusive','image_verified','system_disk_excluded')})
        self.assertFalse(r['authorized'])
        self.assertFalse(r['writing_enabled'])
    def test_all_false_denied(self):
        self.assertFalse(evaluate_write_request()['authorized'])
    def test_non_boolean_denied(self):
        self.assertFalse(evaluate_write_request(polkit_authorized=1)['checks']['polkit_authorized'])
    def test_capabilities_disabled(self):
        self.assertFalse(WriterCapability().writing_enabled)
        self.assertFalse(WriterCapability().polkit_enabled)
    def test_version_and_warning_consistent(self):
        text=(ROOT/'src/main.cpp').read_text()
        self.assertIn('v1.1.0-beta93',text)
        self.assertIn('v1.1.0-beta93 remains READ-ONLY',text)
        self.assertNotIn('Beta 12 remains READ-ONLY',text)
