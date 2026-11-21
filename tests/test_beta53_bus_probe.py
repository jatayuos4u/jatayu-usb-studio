import unittest
from unittest.mock import patch
import beta53_bus_probe as probe

class BusProbeTests(unittest.TestCase):
    def test_missing_daemon_fails(self):
        with patch.object(probe.shutil,'which',return_value=None):
            with self.assertRaisesRegex(RuntimeError,'dbus-daemon'):probe.run()
    def test_transport_only_if_dependencies_available(self):
        try: import dbus_next
        except ImportError: self.skipTest('python3-dbus-next not installed')
        if not probe.shutil.which('dbus-daemon'):self.skipTest('dbus-daemon not installed')
        result=probe.run()
        self.assertTrue(result['private_bus'])
        self.assertFalse(result['writing_enabled'])
        self.assertEqual(result['calls'],3)
