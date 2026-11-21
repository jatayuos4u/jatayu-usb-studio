#!/usr/bin/env python3
"""Beta66 isolated system-bus inspection adapter. NO privileged writing.

Only the real transport message supplies sender. The policy intentionally denies
by default; an administrator must separately configure inspection permissions.
"""
from beta63_service import InspectionService
from beta56_secure_dispatch import dispatch, from_dbus_message
from beta65_polkit import check_polkit_inspection

async def inspect_dispatch(bus, envelope):
    # Existing dispatcher checks unique sender, credentials and method signature.
    # Only InspectAuthorization uses the actual PolicyKit1 authority.
    return await dispatch(bus, envelope, permission_checker=check_polkit_inspection)

class PolkitInspectionService(InspectionService):
    async def _reply(self, msg):
        # Reuse lifecycle, timeout, and cleanup implementation, but dispatch
        # through the real noninteractive Polkit inspection checker.
        from dbus_next import Message
        import asyncio, json
        try:
            result = await asyncio.wait_for(
                inspect_dispatch(self.bus, from_dbus_message(msg)), timeout=8)
        except Exception:
            result = {'ok': False, 'authorized': False, 'writing_enabled': False,
                      'reason': 'Inspection unavailable'}
        if not self.stopping:
            try:
                self.bus.send(Message.new_method_return(msg, signature='s',
                    body=[json.dumps(result)]))
            except Exception:
                pass
