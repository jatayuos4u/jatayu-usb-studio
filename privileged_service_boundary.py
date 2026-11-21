#!/usr/bin/env python3
"""Denial-only boundary for a future system-bus privileged writer.

Separates untrusted caller-supplied claims from verified credentials.
This module does NOT provide a D-Bus service or Polkit authorization.
"""
from writer_protocol import decode_request, ProtocolError

class WriteBoundary:
    def capabilities(self):
        return {"system_bus_registered": False, "polkit_action_installed": False,
                "authenticated_sender": False, "physical_writes_enabled": False,
                "real_device_open_enabled": False}

    def prepare(self, request_bytes, *, sender=None, polkit_result=None):
        try:
            decode_request(request_bytes)
        except ProtocolError as exc:
            return {"ok": False, "authorized": False, "reason": str(exc)}
        # Even an attacker-supplied `sender` or `polkit_result=True` cannot
        # activate a write. Future service must resolve sender from bus daemon.
        return {"ok": False, "authorized": False,
                "reason": "No verified D-Bus sender or installed Polkit authority"}

    def execute(self, *args, **kwargs):
        return {"ok": False, "authorized": False, "writing_enabled": False,
                "reason": "No privileged physical writer is implemented"}
