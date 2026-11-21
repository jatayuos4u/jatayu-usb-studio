"""Beta 49: non-writing privileged-service authorization design test harness.

This module has no write methods. An in-memory challenge is not an authorization
credential and MUST NOT be used as a production privileged backend.
"""
from dataclasses import dataclass
import hashlib
import json
import secrets
import time


class GateRejected(ValueError):
    pass


@dataclass(frozen=True)
class WriteIntent:
    iso_sha256: str
    iso_size_bytes: int
    destination: str
    serial: str
    major_minor: str
    device_size_bytes: int
    caller_uid: int
    caller_bus_name: str


def validate_intent(intent):
    if not isinstance(intent, WriteIntent):
        raise GateRejected('Malformed write intent')
    if not isinstance(intent.iso_sha256, str) or len(intent.iso_sha256) != 64 or any(c not in '0123456789abcdef' for c in intent.iso_sha256):
        raise GateRejected('Invalid ISO digest')
    if not isinstance(intent.iso_size_bytes, int) or isinstance(intent.iso_size_bytes, bool) or intent.iso_size_bytes <= 0:
        raise GateRejected('Invalid ISO size')
    if not isinstance(intent.destination, str) or not intent.destination.startswith('/dev/') or '/' in intent.destination[5:] or not intent.destination[5:].isalnum():
        raise GateRejected('Invalid destination')
    if not isinstance(intent.serial, str) or not intent.serial.strip() or len(intent.serial) > 256:
        raise GateRejected('Missing device serial')
    if not isinstance(intent.major_minor, str) or not intent.major_minor.count(':') == 1 or not all(p.isdigit() for p in intent.major_minor.split(':')):
        raise GateRejected('Invalid kernel device identity')
    if not isinstance(intent.device_size_bytes, int) or isinstance(intent.device_size_bytes, bool) or intent.device_size_bytes < intent.iso_size_bytes:
        raise GateRejected('USB capacity is insufficient')
    if not isinstance(intent.caller_uid, int) or isinstance(intent.caller_uid, bool) or intent.caller_uid < 0:
        raise GateRejected('Invalid caller UID')
    if not isinstance(intent.caller_bus_name, str) or not intent.caller_bus_name.startswith(':') or len(intent.caller_bus_name) > 255:
        raise GateRejected('Caller must have a unique D-Bus sender name')
    return True


def intent_digest(intent):
    validate_intent(intent)
    return hashlib.sha256(json.dumps(intent.__dict__, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


class DryRunGate:
    """Single-use, expiring confirmation challenges for testing ONLY.

    No authorization is granted; no device is opened. In production, the service
    must independently derive caller identity and device facts, not trust these
    fields from the unprivileged GUI.
    """
    def __init__(self, *, clock=None, lifetime_seconds=60):
        self._clock = clock if clock is not None else time.monotonic
        if not 1 <= lifetime_seconds <= 300:
            raise ValueError('Invalid challenge lifetime')
        self._lifetime = lifetime_seconds
        self._pending = {}

    def prepare(self, intent):
        validate_intent(intent)
        challenge = secrets.token_urlsafe(32)
        self._pending[challenge] = (intent_digest(intent), self._clock() + self._lifetime)
        return {'ok': True, 'challenge': challenge, 'authorized': False,
                'writing_enabled': False, 'stage': 'dry_run_confirmation'}

    def confirm(self, intent, challenge):
        # Consume BEFORE validation so a failed attempt cannot be replayed.
        entry = self._pending.pop(challenge, None) if isinstance(challenge, str) else None
        if entry is None:
            raise GateRejected('Unknown or already consumed challenge')
        expected, expires = entry
        if self._clock() >= expires:
            raise GateRejected('Expired challenge')
        if intent_digest(intent) != expected:
            raise GateRejected('Write intent changed after confirmation')
        return {'ok': False, 'authorized': False, 'writing_enabled': False,
                'reason': 'Confirmation matched; privileged USB writer remains unavailable'}


def execute_write(*_args, **_kwargs):
    raise GateRejected('Physical USB writing is not implemented or authorized')
