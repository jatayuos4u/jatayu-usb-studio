#!/usr/bin/env python3
"""Private-bus smoke test of Beta67's actual configured bus name; no writes."""
import asyncio
import json
import os
import select
import shutil
import subprocess
from beta67_system_bus import BUS_NAME, serve
from beta52_system_bus import OBJECT_PATH, INTERFACE
from beta551_dbus_cleanup import close_test_buses

async def check(address):
    from dbus_next.aio import MessageBus
    from dbus_next import Message, MessageType
    server = await MessageBus(bus_address=address).connect()
    client = await MessageBus(bus_address=address).connect()
    stop = asyncio.Event()
    task = asyncio.create_task(serve(server, stop))
    try:
        for _ in range(100):
            if task.done():
                await task
            await asyncio.sleep(.01)
            # Actual request is retried until name ownership is established.
            try:
                response = await asyncio.wait_for(client.call(Message(destination=BUS_NAME,path=OBJECT_PATH,interface=INTERFACE,member='Capabilities')),2)
                if response.message_type == MessageType.METHOD_RETURN:
                    result=json.loads(response.body[0]);assert result['writing_enabled'] is False
                    break
            except Exception:
                pass
        else:
            raise AssertionError('Inspection service not reachable')
        response=await client.call(Message(destination=BUS_NAME,path=OBJECT_PATH,interface=INTERFACE,member='RequestWrite',signature='s',body=['{}']))
        assert response.message_type == MessageType.METHOD_RETURN
        result=json.loads(response.body[0]);assert result.get('writing_enabled') is False and result.get('authorized') is not True
        return {'ok':True,'system_bus_name':BUS_NAME,'writing_enabled':False,'destructive_request_denied':True}
    finally:
        stop.set()
        await task
        await close_test_buses(client)

def run():
    assert shutil.which('dbus-daemon'), 'dbus-daemon required'
    p=subprocess.Popen(['dbus-daemon','--session','--nofork','--print-address=1'],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
    try:
        if not select.select([p.stdout],[],[],5)[0]:raise RuntimeError('Bus startup timeout')
        address=p.stdout.readline().strip()
        return asyncio.run(check(address))
    finally:
        if p.poll() is None:p.terminate()
        try:p.communicate(timeout=3)
        except subprocess.TimeoutExpired:p.kill();p.communicate()
        for stream in (p.stdout,p.stderr):
            if stream and not stream.closed:stream.close()
if __name__ == '__main__':print(json.dumps(run(),sort_keys=True))
