#!/usr/bin/env python3
"""Beta 63 isolated inspection service. Never writes, opens block devices or elevates.

Use a private test bus or a manually provisioned unprivileged bus. Not a root daemon.
"""
import asyncio
import json
from beta52_system_bus import OBJECT_PATH, INTERFACE
from beta56_secure_dispatch import dispatch, from_dbus_message
from beta551_dbus_cleanup import close_test_buses

SERVICE_NAME = 'in.jatayuos.USBStudio.Beta63Inspection'

class InspectionService:
    def __init__(self, bus):
        self.bus = bus
        self.pending = set()
        self.stopping = False
        self.handler = self._handle

    async def start(self):
        await self.bus.request_name(SERVICE_NAME)
        self.bus.add_message_handler(self.handler)

    def _handle(self, msg):
        from dbus_next import MessageType
        if self.stopping or msg.message_type != MessageType.METHOD_CALL:
            return False
        if msg.path != OBJECT_PATH or msg.interface != INTERFACE:
            return False
        task = asyncio.create_task(self._reply(msg))
        self.pending.add(task)
        task.add_done_callback(self.pending.discard)
        return True

    async def _reply(self, msg):
        from dbus_next import Message
        try:
            result = await asyncio.wait_for(dispatch(self.bus, from_dbus_message(msg)), timeout=8)
        except Exception:
            result = {'ok':False,'authorized':False,'writing_enabled':False,'reason':'Request failed'}
        if self.stopping:
            return
        try:
            self.bus.send(Message.new_method_return(msg, signature='s', body=[json.dumps(result)]))
        except Exception:
            pass

    async def stop(self):
        self.stopping = True
        self.bus.remove_message_handler(self.handler)
        for task in tuple(self.pending):
            task.cancel()
        if self.pending:
            await asyncio.gather(*tuple(self.pending), return_exceptions=True)
        await close_test_buses(self.bus)
