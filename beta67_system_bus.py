#!/usr/bin/env python3
"""Beta67 opt-in unprivileged system bus inspection service; no disk access.

Manual installation required. Never execute as root. Does not enable writing.
"""
import asyncio
import os
import signal
from beta66_inspection_service import PolkitInspectionService
from beta63_service import InspectionService
from beta551_dbus_cleanup import close_test_buses

BUS_NAME = 'in.jatayuos.USBStudio.Inspection'

class SystemInspectionService(PolkitInspectionService):
    async def start(self):
        # Override the older Beta63 test bus name with the configured system name.
        await self.bus.request_name(BUS_NAME)
        self.bus.add_message_handler(self.handler)

async def serve(bus=None, stop=None):
    if os.geteuid() == 0:
        raise PermissionError('Inspection service must not run as root')
    if bus is None:
        from dbus_next import BusType
        from dbus_next.aio import MessageBus
        bus = await MessageBus(bus_type=BusType.SYSTEM).connect()
    service = SystemInspectionService(bus)
    try:
        await service.start()
        if stop is None:
            stop = asyncio.Event()
            loop = asyncio.get_running_loop()
            for sig in (signal.SIGTERM, signal.SIGINT):
                try:
                    loop.add_signal_handler(sig, stop.set)
                except (NotImplementedError, RuntimeError):
                    pass
        await stop.wait()
    finally:
        if not service.stopping:
            await service.stop()

if __name__ == '__main__':
    asyncio.run(serve())
