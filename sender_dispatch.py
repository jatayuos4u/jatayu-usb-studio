"""Beta 19: transport-envelope-bound inspection dispatch; never grants write access."""
import json
from sender_identity import resolve_sender
from polkit_inspection import check_inspection_permission
from inspection_request import parse_inspection_request, InvalidInspectionRequest

MAX_REQUEST_BYTES = 16384

def deny(reason):
    return {"ok": False, "authorized": False, "writing_enabled": False, "reason": reason}

async def inspect_sender_request(bus, sender, payload, *, resolver=resolve_sender, permission_checker=check_inspection_permission):
    # The sender MUST originate in the D-Bus Message.sender envelope.
    if not isinstance(payload, str):
        return deny("Invalid request")
    try:
        if len(payload.encode("utf-8")) > MAX_REQUEST_BYTES:
            return deny("Request too large")
        identity = await resolver(bus, sender)
        if identity.unique_name != sender or type(identity.uid) is not int or type(identity.pid) is not int:
            return deny("Untrusted transport identity")
        if identity.uid < 0 or identity.pid <= 0:
            return deny("Invalid transport credentials")
    except Exception:
        return deny("Sender authentication unavailable")
    try:
        parse_inspection_request(payload)
    except InvalidInspectionRequest:
        return deny("Invalid inspection request; writing disabled")
    try:
        allowed = await permission_checker(bus, sender)
    except Exception:
        allowed = False
    if allowed is not True:
        return deny("Polkit inspection permission denied or unavailable; writing disabled")
    return deny("Polkit inspection permission checked; writing remains disabled")
