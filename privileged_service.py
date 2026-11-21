#!/usr/bin/env python3
"""Beta 17 privileged-service boundary, intentionally unprivileged and non-writing.

This is NOT a daemon and must not be installed as a root service.
The Beta 17 authorization contract remains strictly non-writing.
"""
from writer_protocol import decode_request, ProtocolError, PROTOCOL_VERSION
from device_revalidation import DeviceFingerprint, check_live

class PrivilegedWriterBoundary:
    def __init__(self, inspector=None):
        self.inspector = inspector

    def capabilities(self):
        return {'protocol_version': PROTOCOL_VERSION, 'writing_enabled': False,
                'polkit_enabled': False, 'privileged_service_installed': False,
                'device_revalidation': True}

    def prepare(self, payload):
        try:
            request = decode_request(payload)
        except ProtocolError as exc:
            return {'ok': False, 'authorized': False, 'reason': str(exc)}
        expected = DeviceFingerprint(request.target, request.expected_major,
                                     request.expected_minor, request.expected_size,
                                     request.expected_sysfs_path, request.expected_serial)
        report = check_live(expected, **({'inspector': self.inspector} if self.inspector else {}))
        return {'ok': report['ok'], 'authorized': False, 'reason': report['reason'],
                'write_available': False}

    def write(self, payload):
        return {'ok': False, 'authorized': False,
                'reason': 'Beta 17 has no privileged writer; disk writes are disabled'}

    def cancel(self):
        return {'ok': True, 'authorized': False, 'reason': 'No writing job exists'}
