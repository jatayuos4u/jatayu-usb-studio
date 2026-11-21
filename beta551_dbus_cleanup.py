"""Private-bus integration-test cleanup for dbus-next 0.2.x.

The dbus-next socket has a makefile() stream which holds an I/O reference.
Close the stream before the socket; do not use this helper for production.
"""
import asyncio


async def close_test_buses(*buses):
    active = [bus for bus in buses if bus is not None]
    try:
        for bus in active:
            bus.disconnect()
        await asyncio.gather(
            *(bus.wait_for_disconnect() for bus in active),
            return_exceptions=False,
        )
    finally:
        # The event-loop reader/writer are removed by dbus-next finalization.
        # makefile() increments socket._io_refs: close the stream first.
        # Do not set bus._sock = None before the socket has really closed.
        for bus in active:
            stream = getattr(bus, "_stream", None)
            sock = getattr(bus, "_sock", None)
            try:
                if stream is not None:
                    stream.close()
            finally:
                if sock is not None:
                    sock.close()
            if sock is not None and sock.fileno() != -1:
                raise RuntimeError("D-Bus test socket still owns an open descriptor")
        await asyncio.sleep(0)
