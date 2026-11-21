import json
import unittest
from ipc_service import handle_request, BUS_NAME, OBJECT_PATH, INTERFACE

class Beta16IPCTests(unittest.TestCase):
    def test_names(self):
        self.assertEqual(BUS_NAME, "in.jatayuos.USBStudio.Preview")
        self.assertTrue(OBJECT_PATH.startswith("/"))
        self.assertTrue(INTERFACE.endswith("Preview1"))
    def test_capabilities(self):
        self.assertFalse(json.loads(handle_request("Capabilities"))["writing_enabled"])
    def test_unknown_method_denied(self):
        self.assertFalse(json.loads(handle_request("Write"))["authorized"])
    def test_empty_request_denied(self):
        self.assertFalse(json.loads(handle_request("Prepare", ""))["authorized"])
    def test_oversize_denied(self):
        self.assertFalse(json.loads(handle_request("Prepare", "x"*20000))["authorized"])
    def test_invalid_request_denied(self):
        self.assertFalse(json.loads(handle_request("Prepare", "{}"))["authorized"])
    def test_no_system_bus_or_polkit_activation(self):
        import inspect, ipc_service
        s=inspect.getsource(ipc_service)
        self.assertIn("MessageBus().connect()",s)
        self.assertNotIn("BusType.SYSTEM",s)
        self.assertNotIn("pkexec",s)
