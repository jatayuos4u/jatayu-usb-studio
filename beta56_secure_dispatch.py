"""Beta 56: fail-closed sender-bound inspection dispatcher (no device writes).

This is an isolated prototype; it does not install a privileged service.
The D-Bus envelope, not request JSON, supplies sender and method metadata.
"""
import asyncio
import json
from dataclasses import dataclass
from sender_identity import validate_unique_name, resolve_sender
from polkit_inspection import check_inspection_permission

MAX_BODY_BYTES = 4096
ALLOWED = {"Capabilities": "", "InspectAuthorization": "", "RequestWrite": "s"}

@dataclass(frozen=True)
class Envelope:
    sender: str
    member: str
    signature: str
    body: tuple


def deny(reason):
    return {"ok": False, "authorized": False, "writing_enabled": False,
            "reason": reason}


async def dispatch(bus, envelope, *, identity_resolver=resolve_sender,
                   permission_checker=check_inspection_permission):
    """Return inspection results, never a physical-write authorization."""
    if not isinstance(envelope, Envelope):
        return deny("Invalid transport envelope")
    if not validate_unique_name(envelope.sender):
        return deny("Invalid transport sender")
    if envelope.member not in ALLOWED or envelope.signature != ALLOWED[envelope.member]:
        return deny("Unsupported method or signature")
    if type(envelope.body) is not tuple:
        return deny("Invalid argument container")
    if envelope.member == "RequestWrite":
        if len(envelope.body) != 1 or type(envelope.body[0]) is not str:
            return deny("Invalid write request")
        if len(envelope.body[0].encode("utf-8")) > MAX_BODY_BYTES:
            return deny("Write request exceeds limit")
        return deny("Physical USB writing is disabled")
    if envelope.body:
        return deny("Unexpected arguments")
    try:
        identity = await asyncio.wait_for(identity_resolver(bus, envelope.sender), timeout=3)
        if (identity.unique_name != envelope.sender or type(identity.uid) is not int
                or not 0 <= identity.uid <= 0xffffffff or type(identity.pid) is not int
                or not 0 < identity.pid <= 0xffffffff):
            return deny("Sender credential mismatch")
    except Exception:
        return deny("Sender credentials unavailable")
    if envelope.member == "Capabilities":
        return {"ok": True, "authorized": False, "writing_enabled": False,
                "service_mode": "inspection_only", "sender_verified": True}
    try:
        permitted = await asyncio.wait_for(permission_checker(bus, envelope.sender), timeout=3)
    except Exception:
        permitted = False
    return {"ok": True, "authorized": False, "writing_enabled": False,
            "sender_verified": True, "inspection_permission": permitted is True}


def from_dbus_message(msg):
    """Use only transport envelope fields; never deserialize caller identity from JSON."""
    return Envelope(getattr(msg, "sender", None), getattr(msg, "member", None),
                    getattr(msg, "signature", None), tuple(getattr(msg, "body", ()) or ()))
