import unittest
from unittest.mock import Mock
import importlib.util
HAS_DBUS = importlib.util.find_spec("dbus_next") is not None
from beta63_service import InspectionService, SERVICE_NAME

class Beta63ServiceTests(unittest.IsolatedAsyncioTestCase):
    async def test_start_registers_name_and_handler(self):
        bus=Mock(); bus.request_name=__import__('unittest.mock',fromlist=['AsyncMock']).AsyncMock()
        svc=InspectionService(bus)
        await svc.start()
        bus.request_name.assert_awaited_once_with(SERVICE_NAME)
        bus.add_message_handler.assert_called_once_with(svc.handler)

    @unittest.skipUnless(HAS_DBUS, "dbus-next unavailable")
    async def test_stopping_denies_new_requests(self):
        bus=Mock(); svc=InspectionService(bus); svc.stopping=True
        self.assertFalse(svc._handle(Mock()))

    async def test_initial_state_is_nonwriting(self):
        svc=InspectionService(Mock())
        self.assertFalse(svc.stopping)
        self.assertEqual(len(svc.pending),0)

    @unittest.skipUnless(HAS_DBUS, "dbus-next unavailable")
    async def test_wrong_path_ignored(self):
        from dbus_next import MessageType
        svc=InspectionService(Mock())
        msg=Mock(message_type=MessageType.METHOD_CALL,path='/wrong',interface='wrong')
        self.assertFalse(svc._handle(msg))
