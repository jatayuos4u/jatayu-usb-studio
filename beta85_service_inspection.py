#!/usr/bin/env python3
"""Opt-in, unprivileged, read-only D-Bus inspection service prototype.

Not installed by default. Does not access device nodes, authorize or write disks.
The service collects its own live sysfs/proc evidence, never caller-provided snapshots.
"""
import asyncio
import json
import re
import inspect
from beta66_inspection_service import PolkitInspectionService
from beta56_secure_dispatch import from_dbus_message, deny
from sender_identity import resolve_sender, validate_unique_name
from beta83_inspection_cli import report

DEVICE = re.compile(r"/dev/[a-zA-Z0-9_-]{1,64}\Z")
MAX_REPLY = 8192

async def inspect_device(bus, envelope, *, resolver=resolve_sender, inspector=report):
    if not validate_unique_name(getattr(envelope, 'sender', None)):
        return deny('Invalid transport sender')
    if envelope.member != 'InspectDevice' or envelope.signature != 's':
        return deny('Unsupported method or signature')
    if type(envelope.body) is not tuple or len(envelope.body) != 1:
        return deny('Invalid arguments')
    device = envelope.body[0]
    if type(device) is not str or not DEVICE.fullmatch(device) or len(device.encode()) > 96:
        return deny('Invalid device path')
    try:
        identity = await asyncio.wait_for(resolver(bus, envelope.sender), timeout=3)
        if (identity.unique_name != envelope.sender or type(identity.uid) is not int or
            not 0 <= identity.uid <= 0xffffffff or type(identity.pid) is not int or
            not 0 < identity.pid <= 0xffffffff):
            return deny('Transport credentials invalid')
        # A worker thread prevents synchronous sysfs/proc collection blocking the bus.
        if inspect.iscoroutinefunction(inspector):
            result = await asyncio.wait_for(inspector(device), timeout=6)
        else:
            result = await asyncio.wait_for(asyncio.to_thread(inspector, device), timeout=6)
        if (type(result) is not dict or result.get('device') != device or
            result.get('writing_enabled') is not False or
            result.get('status') not in ('BLOCKED', 'ADVISORY_ONLY') or
            type(result.get('candidate')) is not bool or
            type(result.get('reasons')) is not list or
            type(result.get('dependencies')) is not list or
            (result['candidate'] != (result['status'] == 'ADVISORY_ONLY'))):
            return deny('Invalid live inspection evidence')
        if len(json.dumps(result).encode()) > MAX_REPLY:
            return deny('Inspection result too large')
        return {'ok': True, 'authorized': False, 'writing_enabled': False,
                'sender_verified': True, 'inspection_source': 'unprivileged_service_live',
                'device_inspection': result}
    except Exception:
        return deny('Live inspection unavailable')

class Beta85InspectionService(PolkitInspectionService):
    async def _reply(self, msg):
        if getattr(msg, 'member', None) != 'InspectDevice':
            return await super()._reply(msg)
        from dbus_next import Message
        result = await inspect_device(self.bus, from_dbus_message(msg))
        if not self.stopping:
            try:
                self.bus.send(Message.new_method_return(msg, signature='s',
                    body=[json.dumps(result)]))
            except Exception:
                pass

# Separate executable for manual evaluation; never changes the installed service.
async def serve():
    import os
    import signal
    from dbus_next import BusType
    from dbus_next.aio import MessageBus
    from beta67_system_bus import BUS_NAME
    if os.geteuid() == 0:
        raise PermissionError('Inspection service must never run as root')
    bus = await MessageBus(bus_type=BusType.SYSTEM).connect()
    service = Beta85InspectionService(bus)
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
