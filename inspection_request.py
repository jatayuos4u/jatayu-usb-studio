"""Beta 33: strict, bounded, non-authorizing system-bus inspection requests.

No device access, no shell, no disk writes, no privilege grant.
"""
import json
import re

MAX_BYTES = 4096
ALLOWED_ACTIONS = frozenset({'inspect', 'capabilities'})
DEVICE_PATH = re.compile(r'^/dev/(?:sd[a-z]{1,2}|nvme[0-9]{1,3}n[0-9]{1,3}|mmcblk[0-9]{1,3})$')

class InvalidInspectionRequest(ValueError):
    pass

def parse_inspection_request(payload):
    if not isinstance(payload, str):
        raise InvalidInspectionRequest('Request must be text')
    try:
        encoded = payload.encode('utf-8', errors='strict')
    except UnicodeError as exc:
        raise InvalidInspectionRequest('Invalid encoding') from exc
    if len(encoded) > MAX_BYTES:
        raise InvalidInspectionRequest('Request too large')
    try:
        obj = json.loads(payload, parse_constant=lambda _: (_ for _ in ()).throw(ValueError('Nonfinite number')))
    except (ValueError, TypeError) as exc:
        raise InvalidInspectionRequest('Invalid JSON') from exc
    if not isinstance(obj, dict) or set(obj) != {'version', 'action', 'device'}:
        raise InvalidInspectionRequest('Unexpected request fields')
    if type(obj['version']) is not int or obj['version'] != 1:
        raise InvalidInspectionRequest('Unsupported protocol version')
    if not isinstance(obj['action'], str) or obj['action'] not in ALLOWED_ACTIONS:
        raise InvalidInspectionRequest('Unsupported inspection action')
    if not isinstance(obj['device'], str) or not DEVICE_PATH.fullmatch(obj['device']):
        raise InvalidInspectionRequest('Invalid whole-disk path')
    return {'version': 1, 'action': obj['action'], 'device': obj['device']}

def denied_response(reason='Inspection service does not authorize disk operations'):
    return {'ok': False, 'authorized': False, 'writing_enabled': False, 'reason': reason}
