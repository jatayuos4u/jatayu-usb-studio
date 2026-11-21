from beta551_dbus_cleanup import close_test_buses
"""Beta 53: isolated, non-destructive D-Bus transport integration probe.

Requires python3-dbus-next and dbus-daemon. Never connects to system bus,
never installs a service, and never opens a device.
"""
import asyncio
import json
import shutil
import subprocess

from beta52_system_bus import OBJECT_PATH, INTERFACE
from beta56_secure_dispatch import dispatch, from_dbus_message

async def probe(address):
    from dbus_next.aio import MessageBus
    from dbus_next import Message, MessageType
    server = None
    client = None
    try:
        server = await MessageBus(bus_address=address).connect()
        client = await MessageBus(bus_address=address).connect()
    except BaseException:
        await close_test_buses(client, server)
        raise
    name = 'in.jatayuos.USBStudio.Beta57Test'
    await server.request_name(name)
    async def respond(msg):
        try:
            data = await dispatch(server, from_dbus_message(msg))
        except Exception:
            data = {'ok':False, 'authorized':False, 'writing_enabled':False, 'reason':'Internal failure'}
        server.send(Message.new_method_return(msg, signature='s', body=[json.dumps(data)]))
    def handler(msg):
        if msg.message_type != MessageType.METHOD_CALL or msg.path != OBJECT_PATH or msg.interface != INTERFACE:
            return False
        asyncio.create_task(respond(msg))
        return True
    server.add_message_handler(handler)
    try:
        results=[]
        for member,signature,body in [('Capabilities','',[]),('InspectAuthorization','',[]),('RequestWrite','s',['{}']),('EraseDisk','',[])]:
            reply = await asyncio.wait_for(client.call(Message(destination=name,path=OBJECT_PATH,interface=INTERFACE,member=member,signature=signature,body=body)),timeout=4)
            if reply.message_type != MessageType.METHOD_RETURN or reply.signature != 's':
                raise RuntimeError('Unexpected D-Bus response')
            result=json.loads(reply.body[0]); results.append(result)
            if result.get('writing_enabled') is not False or result.get('authorized') is True:
                raise RuntimeError('FAIL: unexpected write authorization')
        if not results[0].get('sender_verified'):
            raise RuntimeError('Sender identity was not verified')
        if results[2].get('authorized') is not False or results[3].get('ok') is not False:
            raise RuntimeError('Unsafe method accepted')
        return {'ok':True,'private_bus':True,'calls':len(results),'writing_enabled':False,'authorized':False}
    finally:
        await close_test_buses(client, server)

def run():
    if not shutil.which('dbus-daemon'):
        raise RuntimeError('dbus-daemon not installed')
    proc=subprocess.Popen(['dbus-daemon','--session','--nofork','--print-address=1'],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
    try:
        import select
        if not select.select([proc.stdout],[],[],5)[0]:
            raise RuntimeError('Private D-Bus startup timeout')
        address=proc.stdout.readline().strip()
        if not address.startswith('unix:'):
            raise RuntimeError('Unexpected private bus address')
        return asyncio.run(probe(address))
    finally:
        if proc.poll() is None:
            proc.terminate()
        try:
            proc.communicate(timeout=3)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.communicate()
        finally:
            if proc.stdout and not proc.stdout.closed: proc.stdout.close()
            if proc.stderr and not proc.stderr.closed: proc.stderr.close()

if __name__=='__main__':
    print(json.dumps(run(),sort_keys=True))
