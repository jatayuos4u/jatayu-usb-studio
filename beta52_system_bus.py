"""Beta 52: non-privileged system-bus service, authorization inspection only.

No block-device I/O. No root installation. This does not grant write access.
"""
import asyncio
import json
from sender_identity import validate_unique_name
from polkit_inspection import check_inspection_permission

BUS_NAME = "in.jatayuos.USBStudio.Inspection"
OBJECT_PATH = "/in/jatayuos/USBStudio/Inspection"
INTERFACE = "in.jatayuos.USBStudio.Inspection1"
ALLOWED = {"Capabilities": "", "InspectAuthorization": "", "RequestWrite": "s"}

def capabilities():
    return {"protocol_version": 3, "service_mode": "system_nonprivileged_inspection",
            "polkit_inspection_available": True, "privileged_backend": False,
            "writing_enabled": False, "installation_enabled": False}

def deny(reason):
    return {"ok": False, "authorized": False, "writing_enabled": False, "reason": reason}

async def handle(member, signature, body, sender, bus):
    if not validate_unique_name(sender):
        return deny("Missing or invalid unique transport sender")
    if member not in ALLOWED or signature != ALLOWED[member]:
        return deny("Unsupported method or signature")
    if member == "Capabilities":
        if body: return deny("Unexpected arguments")
        return capabilities()
    if member == "RequestWrite":
        # No user input can activate physical writing.
        if len(body) != 1 or not isinstance(body[0], str):
            return deny("Invalid request")
        return deny("Physical USB writing is disabled; no privileged writer installed")
    if body:
        return deny("Unexpected arguments")
    permitted = await check_inspection_permission(bus, sender)
    return {"ok": True, "inspection_permission": permitted,
            "authorized": False, "writing_enabled": False,
            "reason": "Noninteractive Polkit inspection only; never write authorization"}

async def serve():
    try:
        from dbus_next import BusType, Message, MessageType
        from dbus_next.aio import MessageBus
    except ImportError as exc:
        raise RuntimeError("python3-dbus-next is required") from exc
    bus = await MessageBus(bus_type=BusType.SYSTEM).connect()
    # Beta 57: all live service requests pass through the sender-bound dispatcher.
    from beta56_secure_dispatch import dispatch, from_dbus_message, deny as secure_deny
    pending = set()

    async def reply(msg):
        try:
            result = await dispatch(bus, from_dbus_message(msg))
        except Exception:
            result = secure_deny("Internal inspection failure")
        # The caller may disconnect while credentials are being resolved.
        try:
            bus.send(Message.new_method_return(
                msg, signature="s", body=[json.dumps(result, sort_keys=True)]))
        except Exception:
            pass  # Never retry, escalate, or perform a write on reply failure.

    def on_message(msg):
        if (msg.message_type != MessageType.METHOD_CALL or msg.path != OBJECT_PATH
                or msg.interface != INTERFACE):
            return False
        task = asyncio.create_task(reply(msg))
        pending.add(task)
        task.add_done_callback(pending.discard)
        return True
    bus.add_message_handler(on_message)
    await bus.request_name(BUS_NAME)
    await asyncio.Future()

if __name__ == "__main__":
    asyncio.run(serve())
