import asyncio
import unittest
from unittest.mock import patch
from beta67_system_bus import BUS_NAME, SystemInspectionService, serve

class Beta67Tests(unittest.TestCase):
    def test_expected_bus_name(self):
        self.assertEqual(BUS_NAME, 'in.jatayuos.USBStudio.Inspection')

    def test_root_is_denied_before_connect(self):
        with patch('beta67_system_bus.os.geteuid', return_value=0):
            with self.assertRaises(PermissionError):
                asyncio.run(serve())

    def test_claims_correct_name(self):
        class FakeBus:
            def __init__(self): self.name=None;self.handler=None
            async def request_name(self,name):self.name=name
            def add_message_handler(self,handler):self.handler=handler
        bus=FakeBus()
        asyncio.run(SystemInspectionService(bus).start())
        self.assertEqual(bus.name,BUS_NAME)
        self.assertTrue(callable(bus.handler))
