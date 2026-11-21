#!/usr/bin/env python3
"""Beta 15: advisory authorization and device state contract, never authorizes writes."""
from dataclasses import dataclass
from typing import Optional

@dataclass(frozen=True)
class Caller:
    uid: int
    pid: int
    authenticated: bool

def validate_caller(caller: Optional[Caller]):
    if not isinstance(caller, Caller):
        return False
    return (type(caller.uid) is int and caller.uid >= 0 and
            type(caller.pid) is int and caller.pid > 0 and
            caller.authenticated is True)

def prepare_authorization(caller, *, polkit_result=False, live_identity=False,
                          no_holders=False, image_verified=False):
    checks = {
        "caller": validate_caller(caller),
        "polkit": polkit_result is True,
        "live_identity": live_identity is True,
        "no_holders": no_holders is True,
        "image_verified": image_verified is True,
    }
    return {"ok": False, "authorized": False, "writing_enabled": False,
            "checks": checks, "reason": "Beta 15 has no activated privileged writer"}

def capabilities():
    return {"writing_enabled": False, "polkit_enabled": False,
            "service_installed": False, "simulation_only": True}
