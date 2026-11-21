from beta551_dbus_cleanup import close_test_buses
"""Beta 54 isolated D-Bus negative tests. Never touches system bus or disks."""
import asyncio
import json
import shutil
import subprocess
from beta52_system_bus import handle, OBJECT_PATH, INTERFACE

async def run_checks(address):
    from dbus_next import Message, MessageType
    from dbus_next.aio import MessageBus
    server = None
    client = None
    try:
        server = await MessageBus(bus_address=address).connect()
        client = await MessageBus(bus_address=address).connect()
    except BaseException:
        await close_test_buses(client, server)
        raise
    name = "in.jatayuos.USBStudio.Beta54Test"
    await server.request_name(name)
    tasks = set()
    async def respond(msg):
        try:
            data = await handle(msg.member, msg.signature, msg.body, msg.sender, server)
        except Exception:
            data = {"ok": False, "authorized": False, "writing_enabled": False, "reason": "Internal failure"}
        server.send(Message.new_method_return(msg, signature="s", body=[json.dumps(data)]))
    def handler(msg):
        if msg.message_type != MessageType.METHOD_CALL or msg.path != OBJECT_PATH or msg.interface != INTERFACE:
            return False
        task = asyncio.create_task(respond(msg))
        tasks.add(task)
        task.add_done_callback(tasks.discard)
        return True
    server.add_message_handler(handler)
    try:
        cases = [
            ("Capabilities", "", []),
            ("RequestWrite", "s", ["{\"authorized\":true,\"writing_enabled\":true}"]),
            ("RequestWrite", "s", ["/dev/sdb"]),
            ("EraseDisk", "", []),
            ("RequestWrite", "", []),
            ("Capabilities", "s", ["unexpected"]),
        ]
        for member, signature, body in cases:
            msg = Message(destination=name, path=OBJECT_PATH, interface=INTERFACE, member=member, signature=signature, body=body)
            reply = await asyncio.wait_for(client.call(msg), timeout=4)
            if reply.message_type != MessageType.METHOD_RETURN or reply.signature != "s":
                raise RuntimeError("Unexpected D-Bus response")
            result = json.loads(reply.body[0])
            if result.get("authorized") is not False and result.get("authorized") is not None:
                raise RuntimeError("Authorization unexpectedly granted")
            if result.get("writing_enabled") is not False:
                raise RuntimeError("Writing unexpectedly enabled")
        return {"ok": True, "private_bus": True, "negative_cases": len(cases), "writing_enabled": False}
    finally:
        if tasks: await asyncio.gather(*tasks, return_exceptions=True)
        await close_test_buses(client, server)

def run():
    if not shutil.which("dbus-daemon"):
        raise RuntimeError("dbus-daemon not installed")
    proc = subprocess.Popen(["dbus-daemon", "--session", "--nofork", "--print-address=1"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    try:
        import select
        if not select.select([proc.stdout], [], [], 5)[0]:
            raise RuntimeError("Private D-Bus startup timeout")
        address = proc.stdout.readline().strip()
        if not address.startswith("unix:"):
            raise RuntimeError("Unexpected private bus address")
        return asyncio.run(run_checks(address))
    finally:
        if proc.poll() is None: proc.terminate()
        try: proc.communicate(timeout=3)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.communicate()
        finally:
            if proc.stdout and not proc.stdout.closed: proc.stdout.close()
            if proc.stderr and not proc.stderr.closed: proc.stderr.close()

if __name__ == "__main__":
    print(json.dumps(run(), sort_keys=True))
