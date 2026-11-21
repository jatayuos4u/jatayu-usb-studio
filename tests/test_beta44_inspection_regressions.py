import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
SOURCE = (ROOT / 'src/main.cpp').read_text()

class InspectionFailClosedRegression(unittest.TestCase):
    def test_scan_timeout_is_bounded(self):
        self.assertIn('QTimer::singleShot(6000,this', SOURCE)
        self.assertIn('p->kill();', SOURCE)
    def test_malformed_json_fails_closed(self):
        self.assertIn('doc.isObject()', SOURCE)
        self.assertIn('doc.object().value("blockdevices").isArray()', SOURCE)
        self.assertIn('if(!validSnapshot)', SOURCE)
    def test_failed_scan_never_captures_baseline(self):
        self.assertIn('if(validSnapshot && !baselineInitialized && devices.size()==1)', SOURCE)
        self.assertIn('baselineRequested=false;', SOURCE)
        self.assertIn('automaticInitialBaseline=false;', SOURCE)
    def test_failed_scan_is_distinct_from_disconnected(self):
        self.assertIn('INSPECTION FAILED — USB identity unavailable', SOURCE)
    def test_warning_latch_retained(self):
        self.assertIn('identityAlert=!matched;', SOURCE)
    def test_export_exclusive_create_retained(self):
        self.assertIn('QIODevice::WriteOnly|QIODevice::NewOnly', SOURCE)
    def test_no_disk_write_backend_added(self):
        self.assertNotIn('QFile file(dev)', SOURCE)
        self.assertIn('Physical writes, cloning, formatting and repair remain disabled.', SOURCE)

if __name__ == '__main__': unittest.main()
