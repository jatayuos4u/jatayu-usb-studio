import tempfile
import unittest
from pathlib import Path
from release_readiness import assess

class Beta46ReadinessTests(unittest.TestCase):
    def test_full_release_never_approved_by_static_review(self):
        result = assess()
        self.assertFalse(result['full_featured_release_ready'])
        self.assertFalse(result['physical_usb_writes_authorized'])
        self.assertFalse(result['checks']['privileged_block_writer_approved'])
    def test_existing_source_tree_passes_static_gate(self):
        result = assess()
        self.assertTrue(result['checks']['source_tree_complete'])
        self.assertTrue(result['checks']['nonwriting_service_static_review'], result['static_findings'])
        self.assertTrue(result['checks']['nonwriting_deployment_template_review'], result['static_findings'])
    def test_missing_sources_fail_closed(self):
        with tempfile.TemporaryDirectory() as temp:
            result = assess(Path(temp))
            self.assertFalse(result['checks']['source_tree_complete'])
            self.assertFalse(result['full_featured_release_ready'])
            self.assertTrue(result['static_findings'])
    def test_debian_package_not_assumed(self):
        result = assess()
        self.assertFalse(result['checks']['debian_source_package_present'])
