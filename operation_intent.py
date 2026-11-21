"""Beta 31: fail-closed, non-authorizing USB operation intent checks.

This module never opens devices, authorizes operations, or performs writes.
It models explicit user acknowledgement and a fresh identity check for a
future privileged service. A successful preview is NOT permission to write.
"""
from dataclasses import dataclass
from device_revalidation import DeviceFingerprint, check_live

OPERATIONS = frozenset({'write_iso', 'clone_usb', 'format_usb', 'repair_usb'})

@dataclass(frozen=True)
class OperationIntent:
    operation: str
    expected: DeviceFingerprint
    confirmation: str

def preview_intent(intent, *, inspector=None):
    base = {'ok': False, 'authorized': False, 'writing_enabled': False}
    if not isinstance(intent, OperationIntent):
        return {**base, 'reason': 'Invalid operation intent'}
    if intent.operation not in OPERATIONS:
        return {**base, 'reason': 'Unsupported operation'}
    if not isinstance(intent.expected, DeviceFingerprint):
        return {**base, 'reason': 'Missing device fingerprint'}
    if intent.confirmation != 'ERASE ' + intent.expected.path:
        return {**base, 'reason': 'Explicit device-specific confirmation required'}
    result = check_live(intent.expected, **({'inspector': inspector} if inspector is not None else {}))
    if not result['ok']:
        return {**base, 'reason': result['reason']}
    return {**base, 'ok': True, 'reason': 'Identity and acknowledgement preview passed; operation still disabled'}
