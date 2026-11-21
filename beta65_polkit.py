#!/usr/bin/env python3
"""Real system-bus Polkit *inspection* check, fail closed.

This module never issues write tickets, installs policies, or writes devices.
Only invoke it inside a trusted system-bus service using the actual message
sender (never a sender supplied in request data).
"""
import asyncio
from sender_identity import validate_unique_name

AUTHORITY = 'org.freedesktop.PolicyKit1'
PATH = '/org/freedesktop/PolicyKit1/Authority'
INTERFACE = 'org.freedesktop.PolicyKit1.Authority'
ACTION = 'in.jatayuos.usbstudio.inspect'

async def check_polkit_inspection(bus, sender, *, timeout=5.0):
    """Check inspection action noninteractively; any error means denied."""
    if not validate_unique_name(sender):
        return False
    if not (isinstance(timeout, (int, float)) and 0 < timeout <= 10):
        return False
    try:
        from dbus_next import Message, MessageType, Variant
        request = Message(destination=AUTHORITY, path=PATH,
            interface=INTERFACE, member='CheckAuthorization',
            signature='(sa{sv})sa{ss}us', body=[
                ('system-bus-name', {'name': Variant('s', sender)}),
                ACTION, {}, 0, '' ])
        response = await asyncio.wait_for(bus.call(request), timeout=timeout)
        if (response is None or response.message_type != MessageType.METHOD_RETURN
                or response.signature != '(bba{ss})' or len(response.body) != 1):
            return False
        result = response.body[0]
        return (isinstance(result, (list, tuple)) and len(result) == 3
                and type(result[0]) is bool and result[0] is True
                and type(result[1]) is bool and isinstance(result[2], dict))
    except Exception:
        return False
