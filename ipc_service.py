"""Beta 16 actual session D-Bus IPC endpoint, strictly unprivileged and non-writing.

Optional dependency: python3-dbus-next. Not a system bus service.
The session bus authenticates local peers. No privileged operations are offered.
"""
import json
from privileged_service import PrivilegedWriterBoundary

BUS_NAME = "in.jatayuos.USBStudio.Preview"
OBJECT_PATH = "/in/jatayuos/USBStudio/Preview"
INTERFACE = "in.jatayuos.USBStudio.Preview1"

def handle_request(method, payload=""):
    boundary = PrivilegedWriterBoundary()
    if method == "Capabilities":
        return json.dumps(boundary.capabilities(), sort_keys=True)
    if method == "Prepare":
        # Decode request through the existing bounded protocol; no writing.
        if not isinstance(payload, str) or len(payload.encode("utf-8")) > 16384:
            return json.dumps({"ok": False, "authorized": False, "reason": "Oversized request"})
        return json.dumps(boundary.prepare(payload.encode("utf-8")), sort_keys=True)
    return json.dumps({"ok": False, "authorized": False, "reason": "Unknown method"})

async def serve():
    try:
        from dbus_next.aio import MessageBus
        from dbus_next.service import ServiceInterface, method
    except ImportError as exc:
        raise RuntimeError("Install python3-dbus-next to use the optional IPC preview") from exc

    class Preview(ServiceInterface):
        def __init__(self):
            super().__init__(INTERFACE)

        @method()
        def Capabilities(self) -> "s":
            return handle_request("Capabilities")

        @method()
        def Prepare(self, request: "s") -> "s":
            return handle_request("Prepare", request)

    bus = await MessageBus().connect()
    await bus.request_name(BUS_NAME)
    bus.export(OBJECT_PATH, Preview())
    import asyncio
    await asyncio.Future()

if __name__ == "__main__":
    import asyncio
    asyncio.run(serve())
