#!/usr/bin/env python3
"""Beta 10: strict, non-destructive privileged-writer protocol prototype.

No block-device writes, privilege escalation, or authorization are implemented.
All requests are rejected by the service boundary.
"""
import json
import re
from dataclasses import dataclass

MAX_REQUEST_BYTES = 8192
PROTOCOL_VERSION = 2
DEVICE_RE = re.compile(r"/dev/[a-zA-Z0-9]+\Z")

class ProtocolError(ValueError):
    pass

@dataclass(frozen=True)
class PrepareRequest:
    version: int
    target: str
    iso_path: str
    expected_major: int
    expected_minor: int
    expected_size: int
    expected_sysfs_path: str
    expected_serial: str


def decode_request(payload):
    if not isinstance(payload, bytes) or len(payload) > MAX_REQUEST_BYTES:
        raise ProtocolError('Request must be bounded bytes')
    try:
        value = json.loads(payload.decode('utf-8'))
    except (UnicodeError, ValueError) as e:
        raise ProtocolError('Malformed request') from e
    keys = set(PrepareRequest.__dataclass_fields__)
    if not isinstance(value, dict) or set(value) != keys:
        raise ProtocolError('Unexpected request fields')
    if type(value['version']) is not int or value['version'] != PROTOCOL_VERSION:
        raise ProtocolError('Unsupported protocol version')
    if not isinstance(value['target'], str) or not DEVICE_RE.fullmatch(value['target']):
        raise ProtocolError('Invalid target')
    if not isinstance(value['iso_path'], str) or not value['iso_path'].startswith('/') or '\x00' in value['iso_path']:
        raise ProtocolError('Invalid ISO path')
    for key in ('expected_major','expected_minor','expected_size'):
        if type(value[key]) is not int or value[key] < 0:
            raise ProtocolError('Invalid device identity')
    if value['expected_size'] == 0:
        raise ProtocolError('Zero capacity')
    for key in ('expected_sysfs_path','expected_serial'):
        if not isinstance(value[key], str) or len(value[key]) > 4096 or '\x00' in value[key]:
            raise ProtocolError('Invalid identity field')
    if not value['expected_sysfs_path'].startswith('/sys/'):
        raise ProtocolError('Invalid sysfs path')
    return PrepareRequest(**value)

class WriterServicePrototype:
    def capabilities(self):
        return {'protocol_version': PROTOCOL_VERSION, 'writing_enabled': False,
                'polkit_authorization_enabled': False, 'real_device_open_enabled': False}

    def handle(self, action, payload=b''):
        if action == 'capabilities':
            return self.capabilities()
        if action not in ('prepare','write','cancel'):
            return {'ok': False, 'authorized': False, 'reason': 'Unknown operation'}
        try:
            if action in ('prepare','write'):
                decode_request(payload)
        except ProtocolError as e:
            return {'ok': False, 'authorized': False, 'reason': str(e)}
        return {'ok': False, 'authorized': False,
                'reason': 'Beta 10 service prototype is read-only; privileged writing is not installed'}
