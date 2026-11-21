#!/usr/bin/env python3
"""Read-only checks against the real system bus; no installation or device access."""
import asyncio, json
from beta68_real_bus_audit import audit
from beta67_system_bus import BUS_NAME
from beta52_system_bus import OBJECT_PATH, INTERFACE

async def check():
    from dbus_next import BusType, Message, MessageType
    from dbus_next.aio import MessageBus
    from beta551_dbus_cleanup import close_test_buses
    baseline = await audit()
    if not baseline.get('ok'):
        return {'ok':False, 'baseline':baseline, 'status':'INSPECTION_NOT_READY'}
    bus = await asyncio.wait_for(MessageBus(bus_type=BusType.SYSTEM).connect(), 5)
    try:
        reply = await asyncio.wait_for(bus.call(Message(destination=BUS_NAME,path=OBJECT_PATH,
            interface=INTERFACE,member='RequestWrite',signature='s',body=['{}'])),5)
        if reply.message_type != MessageType.METHOD_RETURN or reply.signature != 's' or len(reply.body) != 1:
            return {'ok':False,'status':'WRITE_DENIAL_MISSING'}
        value = json.loads(reply.body[0])
        safe = type(value) is dict and value.get('authorized') is False and value.get('writing_enabled') is False and value.get('ok') is False
        return {'ok':safe,'status':'NON_WRITING_SERVICE_VERIFIED' if safe else 'UNSAFE_WRITE_RESPONSE','writing_enabled':False}
    finally:
        await close_test_buses(bus)

if __name__=='__main__':
    try: result=asyncio.run(check())
    except Exception as exc: result={'ok':False,'status':'AUDIT_FAILED','error_type':type(exc).__name__}
    print(json.dumps(result,sort_keys=True))
    raise SystemExit(0 if result.get('ok') else 2)
