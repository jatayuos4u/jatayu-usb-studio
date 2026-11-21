#!/usr/bin/env python3
"""Private-bus service lifecycle test. No device access."""
import asyncio
import json
import subprocess
import shutil
import select
import warnings
from beta63_service import InspectionService, SERVICE_NAME
from beta52_system_bus import OBJECT_PATH, INTERFACE
from beta551_dbus_cleanup import close_test_buses

async def exercise(address):
    from dbus_next.aio import MessageBus
    from dbus_next import Message, MessageType
    server = await MessageBus(bus_address=address).connect()
    client = None
    service = InspectionService(server)
    try:
        await service.start()
        client = await MessageBus(bus_address=address).connect()
        results=[]
        for member, signature, body in [('Capabilities','',[]),('InspectAuthorization','',[]),('RequestWrite','s',['{}']),('EraseDisk','',[])]:
            reply = await asyncio.wait_for(client.call(Message(destination=SERVICE_NAME,path=OBJECT_PATH,interface=INTERFACE,member=member,signature=signature,body=body)), timeout=5)
            assert reply.message_type == MessageType.METHOD_RETURN and reply.signature == 's'
            result=json.loads(reply.body[0])
            assert result.get('writing_enabled') is False and result.get('authorized') is not True
            results.append(result)
        assert results[0].get('sender_verified') is True
        await service.stop()
        return {'ok':True,'calls':len(results),'service_stopped':service.stopping,'writing_enabled':False}
    finally:
        if not service.stopping:
            await service.stop()
        await close_test_buses(client)

def run():
    assert shutil.which('dbus-daemon'), 'dbus-daemon required'
    proc=subprocess.Popen(['dbus-daemon','--session','--nofork','--print-address=1'],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
    try:
        if not select.select([proc.stdout],[],[],5)[0]: raise RuntimeError('Bus startup timeout')
        address=proc.stdout.readline().strip()
        if not address.startswith('unix:'): raise RuntimeError('Invalid private bus address')
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter('always', ResourceWarning)
            result=asyncio.run(exercise(address))
        errors=[str(w.message) for w in caught if issubclass(w.category, ResourceWarning)]
        if errors: raise RuntimeError('Resource warnings: '+repr(errors))
        result['resource_warnings']=0
        return result
    finally:
        if proc.poll() is None: proc.terminate()
        try: proc.communicate(timeout=3)
        except subprocess.TimeoutExpired:
            proc.kill(); proc.communicate()
        for pipe in (proc.stdout,proc.stderr):
            if pipe and not pipe.closed: pipe.close()

if __name__ == '__main__':
    print(json.dumps(run(),sort_keys=True))
