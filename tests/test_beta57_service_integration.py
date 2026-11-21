import ast
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

class Beta57ServiceIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = (ROOT / 'beta52_system_bus.py').read_text()
        cls.tree = ast.parse(cls.source)

    def test_service_imports_secure_dispatch(self):
        self.assertIn('from beta56_secure_dispatch import dispatch, from_dbus_message', self.source)

    def test_service_routes_real_messages_to_dispatch(self):
        self.assertIn('await dispatch(bus, from_dbus_message(msg))', self.source)

    def test_service_no_longer_calls_legacy_handler(self):
        serve = next(node for node in self.tree.body if isinstance(node, ast.AsyncFunctionDef) and node.name == 'serve')
        calls = [n for n in ast.walk(serve) if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)]
        self.assertNotIn('handle', [n.func.id for n in calls])

    def test_service_tracks_pending_tasks(self):
        self.assertIn('pending.add(task)', self.source)
        self.assertIn('task.add_done_callback(pending.discard)', self.source)

    def test_probe_checks_sender_verification(self):
        probe = (ROOT / 'beta57_bus_probe.py').read_text()
        self.assertIn("results[0].get('sender_verified')", probe)

    def test_audit_fails_on_resource_warnings(self):
        audit = (ROOT / 'beta57_integration_audit.py').read_text()
        self.assertIn('error::ResourceWarning', audit)
        self.assertIn('"ResourceWarning" in result.stderr', audit)

    def test_no_device_write_enabled(self):
        self.assertIn('"writing_enabled": False', (ROOT / 'beta56_secure_dispatch.py').read_text())
