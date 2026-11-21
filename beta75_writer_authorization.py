#!/usr/bin/env python3
"""Beta75: non-writing authorization boundary, NOT a privileged service.

A trusted future service must derive the sender from its D-Bus message and
verify the actual UID/device/ISO independently. This module never opens a
block device, invokes Polkit, or grants operating-system privileges.
"""
from dataclasses import dataclass
from beta64_authorization import Denied, TicketStore, WriteIntent

@dataclass(frozen=True)
class VerifiedContext:
    sender: str
    uid: int
    device_major_minor: str
    device_sysfs: str
    iso_sha256: str
    iso_size: int

    def as_intent(self):
        intent = WriteIntent(self.sender, self.uid, self.device_major_minor,
                             self.device_sysfs, self.iso_sha256, self.iso_size)
        intent.validate()
        return intent

class AuthorizationBoundary:
    """No public authorization toggle; only a trusted injected verifier.

    A production backend MUST implement actual system-bus credential checks,
    Polkit authorization, and device/ISO revalidation before use.
    """
    def __init__(self, *, verifier=None, tickets=None):
        self._verifier = verifier
        self._tickets = tickets if tickets is not None else TicketStore()

    def prepare(self, request, *, observed_sender):
        if not callable(self._verifier):
            raise Denied('Trusted verification backend not installed')
        if not isinstance(observed_sender, str) or not observed_sender.startswith(':'):
            raise Denied('Missing authenticated bus sender')
        # The verifier is responsible for independently obtaining UID,
        # device identity and ISO properties, not trusting request fields.
        verified = self._verifier(request, observed_sender)
        if not isinstance(verified, VerifiedContext):
            raise Denied('Verification failed')
        intent = verified.as_intent()
        if intent.sender != observed_sender:
            raise Denied('Authenticated sender mismatch')
        return intent

    def request_ticket(self, request, *, observed_sender):
        # Deliberately cannot issue a ticket. A future trusted service must
        # perform a real Polkit check and define a separate audited entrypoint.
        self.prepare(request, observed_sender=observed_sender)
        raise Denied('Privileged Polkit writer backend not implemented')

    def request_write(self, *args, **kwargs):
        raise Denied('Physical writing disabled')

    def status(self):
        return {'ok': True, 'mode': 'authorization-prototype',
                'writing_enabled': False, 'privileged_service_installed': False}
