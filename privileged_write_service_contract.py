#!/usr/bin/env python3
"""Beta 50: fail-closed boundary for future system-bus write integration.

No privileged daemon, Polkit grant, physical device open, or disk write exists.
This class deliberately cannot authorize or execute a write request.
"""
from writer_protocol import decode_request, ProtocolError

class PhysicalWriteServiceContract:
    def capabilities(self):
        return {"api_version": 1, "system_bus_service_installed": False,
                "polkit_authorization_enabled": False, "physical_write_enabled": False,
                "supports_cancellation": False, "supports_readback": False}

    def prepare(self, payload, *, caller=None):
        try:
            decode_request(payload)
        except ProtocolError as exc:
            return {"ok": False, "authorized": False, "reason": str(exc)}
        return {"ok": False, "authorized": False,
                "reason": "No authenticated system-bus/Polkit writer is installed"}

    def write(self, payload, *, caller=None):
        return {"ok": False, "authorized": False, "writing_enabled": False,
                "reason": "Physical USB writes are disabled pending privileged backend review"}

    def cancel(self, job_id=None):
        return {"ok": False, "authorized": False, "reason": "No physical writing job exists"}
