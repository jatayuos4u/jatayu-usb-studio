"""Beta 20 system D-Bus non-privileged preview with sender-aware dispatch.

Never run as root. Non-interactive Polkit inspection probe; no device access or destructive API.
"""
import asyncio
import json
from sender_dispatch import inspect_sender_request, deny

BUS_NAME = 'in.jatayuos.USBStudio.Inspection'
OBJECT_PATH = '/in/jatayuos/USBStudio/Inspection'
INTERFACE = 'in.jatayuos.USBStudio.Inspection1'

def capabilities():
    return {'protocol_version': 2, 'writing_enabled': False,
            'polkit_enabled': False, 'system_bus_preview': True,
            'privileged': False, 'device_revalidation': False,
            'sender_aware_prepare': True}

def reject_request(_request=''):
    return deny('System bus preview cannot authorize writes')

async def serve():
    try:
        from dbus_next import BusType, Message, MessageType
        from dbus_next.aio import MessageBus
    except ImportError as exc:
        raise RuntimeError('Install python3-dbus-next') from exc

    bus = await MessageBus(bus_type=BusType.SYSTEM).connect()

    async def dispatch(msg):
        try:
            if msg.member == 'Capabilities' and msg.signature == '' and not msg.body:
                result = capabilities()
            elif msg.member == 'Prepare' and msg.signature == 's' and len(msg.body) == 1:
                result = await inspect_sender_request(bus, msg.sender, msg.body[0])
            else:
                result = deny('Unsupported method or signature')
            bus.send(Message.new_method_return(msg, signature='s', body=[json.dumps(result, sort_keys=True)]))
        except Exception:
            bus.send(Message.new_method_return(msg, signature='s', body=[json.dumps(deny('Internal failure'))]))

    def on_message(msg):
        if (msg.message_type != MessageType.METHOD_CALL or msg.path != OBJECT_PATH
                or msg.interface != INTERFACE or msg.member not in ('Capabilities', 'Prepare')):
            return False
        # Low-level handler preserves msg.sender; ServiceInterface methods do not.
        asyncio.create_task(dispatch(msg))
        return True

    bus.add_message_handler(on_message)
    await bus.request_name(BUS_NAME)
    await asyncio.Future()

if __name__ == '__main__':
    asyncio.run(serve())
