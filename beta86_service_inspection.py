#!/usr/bin/env python3
"""Bounded, non-writing system-bus inspection service for Beta 86.

Opt-in service; remains unprivileged. Limits queued and running inspections.
Timeouts cannot forcibly kill a running worker thread: capacity remains reserved
until it finishes, preventing an unbounded thread backlog.
"""
import asyncio
import json
import os
import signal
from concurrent.futures import ThreadPoolExecutor
from beta85_service_inspection import inspect_device, Beta85InspectionService
from beta56_secure_dispatch import from_dbus_message, deny
from beta67_system_bus import BUS_NAME
from beta83_inspection_cli import report

class InspectionLimiter:
    def __init__(self, workers=2):
        self.workers = workers
        self.executor = ThreadPoolExecutor(max_workers=workers, thread_name_prefix='usb-inspect')
        self.active = 0
        self.closed = False

    async def inspect(self, device):
        if self.closed or self.active >= self.workers:
            raise RuntimeError('Inspection busy or shutting down')
        self.active += 1
        loop = asyncio.get_running_loop()
        fut = loop.run_in_executor(self.executor, report, device)
        def release(_):
            self.active -= 1
        fut.add_done_callback(release)
        # Shield keeps a timed-out job counted until it actually finishes.
        return await asyncio.shield(fut)

    def close(self):
        self.closed = True
        self.executor.shutdown(wait=False, cancel_futures=True)

class Beta86InspectionService(Beta85InspectionService):
    def __init__(self, bus, *, workers=2):
        super().__init__(bus)
        self.limiter = InspectionLimiter(workers)

    async def _reply(self, msg):
        if getattr(msg, 'member', None) != 'InspectDevice':
            return await super()._reply(msg)
        if self.limiter.closed or self.limiter.active >= self.limiter.workers:
            result = deny('Inspection service busy or shutting down')
        else:
            # inspect_device validates sender, args and result before returning.
            result = await inspect_device(self.bus, from_dbus_message(msg),
                                          inspector=self.limiter.inspect)
        if not self.stopping:
            try:
                self.bus.send(Message.new_method_return(msg, signature='s', body=[json.dumps(result)]))
            except Exception:
                pass

    async def stop(self):
        self.limiter.close()
        await super().stop()

async def serve():
    if os.geteuid() == 0:
        raise PermissionError('Inspection service must never run as root')
    from dbus_next import BusType
    from dbus_next.aio import MessageBus
    bus = await MessageBus(bus_type=BusType.SYSTEM).connect()
    service = Beta86InspectionService(bus)
    try:
        await service.start()
        stop = asyncio.Event()
        loop = asyncio.get_running_loop()
        for sig in (signal.SIGINT, signal.SIGTERM):
            try: loop.add_signal_handler(sig, stop.set)
            except (RuntimeError, NotImplementedError): pass
        await stop.wait()
    finally:
        await service.stop()

if __name__ == '__main__':
    asyncio.run(serve())
