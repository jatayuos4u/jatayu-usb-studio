import asyncio
import socket
import unittest
from unittest.mock import Mock
from beta551_dbus_cleanup import close_test_buses

class StreamCleanupTests(unittest.IsolatedAsyncioTestCase):
    async def test_makefile_ref_is_closed_before_socket(self):
        left, right = socket.socketpair()
        try:
            stream = left.makefile('rwb')
            bus = Mock()
            bus._stream = stream
            bus._sock = left
            async def wait(): return None
            bus.wait_for_disconnect = wait
            await close_test_buses(bus)
            self.assertTrue(stream.closed)
            self.assertEqual(left.fileno(), -1)
        finally:
            left.close()
            right.close()

    async def test_stream_closes_even_when_wait_fails(self):
        left, right = socket.socketpair()
        try:
            stream = left.makefile('rwb')
            bus = Mock(_stream=stream, _sock=left)
            async def wait(): raise RuntimeError('disconnect failed')
            bus.wait_for_disconnect = wait
            with self.assertRaisesRegex(RuntimeError, 'disconnect failed'):
                await close_test_buses(bus)
            self.assertTrue(stream.closed)
            self.assertEqual(left.fileno(), -1)
        finally:
            left.close()
            right.close()
