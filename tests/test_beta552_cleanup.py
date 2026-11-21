import asyncio
import unittest
from unittest.mock import Mock
from beta551_dbus_cleanup import close_test_buses

class CleanupTests(unittest.IsolatedAsyncioTestCase):
    async def test_closes_even_when_marked_closed(self):
        sock = Mock(); sock._closed = True
        bus = Mock(); bus._sock = sock; bus._stream = Mock(); sock.fileno.return_value = -1
        async def disconnected(): return None
        bus.wait_for_disconnect = disconnected
        await close_test_buses(bus)
        bus.disconnect.assert_called_once()
        sock.close.assert_called_once()
        bus._stream.close.assert_called_once()
        self.assertIs(bus._sock, sock)

    async def test_no_connections(self):
        await close_test_buses(None, None)
