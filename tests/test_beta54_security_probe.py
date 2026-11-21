import unittest
from unittest.mock import patch
import beta54_security_probe as probe

class Beta54SecurityProbeTests(unittest.TestCase):
    def test_missing_daemon_fails_closed(self):
        with patch.object(probe.shutil, "which", return_value=None):
            with self.assertRaisesRegex(RuntimeError, "dbus-daemon"):
                probe.run()

    def test_private_bus_negative_cases(self):
        try: import dbus_next
        except ImportError: self.skipTest("python3-dbus-next unavailable")
        if not probe.shutil.which("dbus-daemon"):
            self.skipTest("dbus-daemon unavailable")
        result = probe.run()
        self.assertTrue(result["ok"])
        self.assertTrue(result["private_bus"])
        self.assertEqual(result["negative_cases"], 6)
        self.assertFalse(result["writing_enabled"])
