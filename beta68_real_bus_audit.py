#!/usr/bin/env python3
"""Non-destructive real system-bus audit. Never installs, starts, or writes.

Tests whether the configured inspection name is already owned on the real
system bus and, if so, that its capabilities deny writing. Absence is reported
as NOT INSTALLED, not as successful deployment.
"""
import asyncio
import json
from beta67_system_bus import BUS_NAME
from beta52_system_bus import OBJECT_PATH, INTERFACE

async def audit(bus=None):
    from dbus_next import BusType, Message, MessageType
    from dbus_next.aio import MessageBus
    owned_bus = bus is None
    if owned_bus:
        bus = await asyncio.wait_for(MessageBus(bus_type=BusType.SYSTEM).connect(), 5)
    try:
        reply = await asyncio.wait_for(bus.call(Message(destination='org.freedesktop.DBus',
            path='/org/freedesktop/DBus', interface='org.freedesktop.DBus',
            member='NameHasOwner', signature='s', body=[BUS_NAME])), 5)
        if reply.message_type != MessageType.METHOD_RETURN or reply.signature != 'b' or len(reply.body) != 1 or type(reply.body[0]) is not bool:
            return {'ok':False,'status':'BUS_QUERY_FAILED','writing_enabled':False}
        if not reply.body[0]:
            return {'ok':False,'status':'NOT_INSTALLED_OR_INACTIVE','writing_enabled':False,
                    'note':'Private-bus tests do not establish real system-bus deployment'}
        reply = await asyncio.wait_for(bus.call(Message(destination=BUS_NAME,
            path=OBJECT_PATH,interface=INTERFACE,member='Capabilities')),5)
        if reply.message_type != MessageType.METHOD_RETURN or reply.signature != 's' or len(reply.body) != 1:
            return {'ok':False,'status':'CAPABILITIES_FAILED','writing_enabled':False}
        value=json.loads(reply.body[0]); safe=(type(value) is dict and value.get('writing_enabled') is False
            and value.get('authorized') is False and value.get('service_mode') == 'inspection_only')
        return {'ok':safe,'status':'INSPECTION_ONLY' if safe else 'UNSAFE_OR_UNEXPECTED_RESPONSE',
                'writing_enabled':False,'real_system_bus':True}
    finally:
        if owned_bus:
            from beta551_dbus_cleanup import close_test_buses
            await close_test_buses(bus)

if __name__=='__main__':
    try:
        result=asyncio.run(audit())
    except Exception as exc:
        result={'ok':False,'status':'SYSTEM_BUS_UNAVAILABLE','writing_enabled':False,
                'error_type':type(exc).__name__}
    print(json.dumps(result,sort_keys=True))
    # Nonzero means the real deployment is not validated.
    raise SystemExit(0 if result.get('ok') else 2)
