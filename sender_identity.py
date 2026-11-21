"""Non-writing prototype for looking up D-Bus transport-verified sender credentials.

Caller-supplied usernames, UIDs, PIDs and well-known bus names are not trusted.
This is a standalone resolver, NOT wired into the service's exported methods:
python-dbus-next ServiceInterface methods do not expose the sender directly.
"""
from dataclasses import dataclass

@dataclass(frozen=True)
class SenderIdentity:
    unique_name: str
    uid: int
    pid: int


def validate_unique_name(sender):
    if not isinstance(sender, str) or not sender.startswith(':') or len(sender) > 255:
        return False
    parts = sender[1:].split('.')
    return len(parts) >= 2 and all(part.isascii() and part.isdigit() and part for part in parts)


async def resolve_sender(bus, sender):
    """Query org.freedesktop.DBus for identity, deny on any malformed response.

    Caller must supply the unique sender from the transport message envelope,
    NEVER from a method argument or JSON request.
    """
    if not validate_unique_name(sender):
        raise ValueError('Untrusted sender name')
    from dbus_next import Message, MessageType
    async def query(member):
        reply = await bus.call(Message(destination='org.freedesktop.DBus',
            path='/org/freedesktop/DBus', interface='org.freedesktop.DBus',
            member=member, signature='s', body=[sender]))
        if reply is None or reply.message_type != MessageType.METHOD_RETURN or reply.signature != 'u':
            raise PermissionError('Credential query failed')
        if len(reply.body) != 1 or type(reply.body[0]) is not int or not 0 <= reply.body[0] <= 0xffffffff:
            raise PermissionError('Invalid credential response')
        return reply.body[0]
    uid = await query('GetConnectionUnixUser')
    pid = await query('GetConnectionUnixProcessID')
    if pid == 0:
        raise PermissionError('Invalid PID')
    return SenderIdentity(sender, uid, pid)


def authorization_decision(identity, polkit_authorized=False):
    """Deliberate hard denial; a valid identity or Polkit flag cannot enable writes."""
    return {'authorized': False, 'writing_enabled': False,
            'reason': 'Beta 18 cannot authorize destructive operations'}
