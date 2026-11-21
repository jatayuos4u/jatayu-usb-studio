"""Beta 20 non-interactive Polkit authorization probe, never a write grant.

Checks are tied to the unique system-bus sender, not UID/PID or JSON values.
The example action is intentionally not installed; an unknown action fails closed.
"""
from sender_identity import validate_unique_name

AUTHORITY = 'org.freedesktop.PolicyKit1'
AUTHORITY_PATH = '/org/freedesktop/PolicyKit1/Authority'
AUTHORITY_IFACE = 'org.freedesktop.PolicyKit1.Authority'
ACTION_ID = 'in.jatayuos.usbstudio.inspect'

async def check_inspection_permission(bus, sender):
    """Return True only for a valid non-interactive Polkit response.

    A True result NEVER authorizes disk access or USB writing.
    """
    if not validate_unique_name(sender):
        return False
    try:
        from dbus_next import Message, MessageType, Variant
        msg = Message(destination=AUTHORITY, path=AUTHORITY_PATH,
            interface=AUTHORITY_IFACE, member='CheckAuthorization',
            signature='(sa{sv})sa{ss}us', body=[
                ('system-bus-name', {'name': Variant('s', sender)}),
                ACTION_ID, {}, 0, ''
            ])
        reply = await bus.call(msg)
        if (reply is None or reply.message_type != MessageType.METHOD_RETURN
                or reply.signature != '(bba{ss})' or len(reply.body) != 1):
            return False
        result = reply.body[0]
        if (not isinstance(result, (tuple, list)) or len(result) != 3
                or type(result[0]) is not bool or type(result[1]) is not bool
                or not isinstance(result[2], dict)):
            return False
        # No interactive authentication, even if Polkit reports challenge possible.
        return result[0] is True
    except Exception:
        return False
