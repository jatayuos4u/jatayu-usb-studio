import unittest
from unittest.mock import patch
import asyncio
from beta68_real_bus_audit import audit

@unittest.skipUnless(__import__("importlib").util.find_spec("dbus_next"), "dbus-next unavailable")
class TestRealBusAudit(unittest.TestCase):
    def test_absent_name_is_not_success(self):
        from dbus_next import MessageType
        class Reply:
            message_type=MessageType.METHOD_RETURN
            signature='b'
            body=[False]
        class Bus:
            async def call(self, msg):
                return Reply()
        result=asyncio.run(audit(Bus()))
        self.assertFalse(result['ok'])
        self.assertEqual(result['status'],'NOT_INSTALLED_OR_INACTIVE')
        self.assertFalse(result['writing_enabled'])

    def test_wrong_owner_response_is_failure(self):
        from dbus_next import MessageType
        class Reply:
            message_type=MessageType.ERROR
            signature=''
            body=[]
        class Bus:
            async def call(self, msg): return Reply()
        result=asyncio.run(audit(Bus()))
        self.assertFalse(result['ok'])
