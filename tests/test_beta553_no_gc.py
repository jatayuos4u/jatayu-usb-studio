import inspect
import unittest
from beta551_dbus_cleanup import close_test_buses

class NoPrematureGCTests(unittest.TestCase):
    def test_cleanup_does_not_force_gc(self):
        source = inspect.getsource(close_test_buses)
        self.assertNotIn('gc.collect(', source)
