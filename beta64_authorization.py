#!/usr/bin/env python3
"""Fail-closed, single-use authorization ticket state machine for future writer.

NOT an authorization authority. Tickets can only be issued after an external,
trusted Polkit decision; this module does not perform Polkit checks and cannot
write devices. A ticket binds a caller and exact ISO/device identity to a short
lifetime. The privileged service must independently revalidate all properties.
"""
from dataclasses import dataclass
import hashlib
import hmac
import secrets
import time

class Denied(Exception):
    pass

@dataclass(frozen=True)
class WriteIntent:
    sender: str
    uid: int
    device_major_minor: str
    device_sysfs: str
    iso_sha256: str
    iso_size: int

    def validate(self):
        if not isinstance(self.sender, str) or not self.sender.startswith(':') or len(self.sender)>128:
            raise Denied('Invalid unique D-Bus sender')
        if type(self.uid) is not int or self.uid < 0:
            raise Denied('Invalid sender UID')
        if not isinstance(self.device_major_minor,str) or not self.device_major_minor.replace(':','').isdigit() or self.device_major_minor.count(':') != 1:
            raise Denied('Invalid block identity')
        if not isinstance(self.device_sysfs,str) or not self.device_sysfs.startswith('/sys/devices/') or len(self.device_sysfs)>1024:
            raise Denied('Invalid physical device path')
        if not isinstance(self.iso_sha256,str) or len(self.iso_sha256)!=64 or any(c not in '0123456789abcdef' for c in self.iso_sha256):
            raise Denied('Invalid ISO checksum')
        if type(self.iso_size) is not int or not 0 < self.iso_size <= 128*1024**3:
            raise Denied('Invalid ISO size')

class TicketStore:
    def __init__(self, *, clock=time.monotonic, ttl=30):
        if not 0 < ttl <= 60: raise ValueError('TTL outside safe range')
        self._clock=clock
        self._ttl=ttl
        self._tickets={}

    def issue(self, intent, *, polkit_authorized=False):
        intent.validate()
        if polkit_authorized is not True:
            raise Denied('Independent Polkit authorization required')
        token=secrets.token_hex(32)
        self._tickets[token]=(intent,self._clock()+self._ttl)
        return token

    def consume(self, token, intent):
        intent.validate()
        if not isinstance(token,str) or len(token)!=64:
            raise Denied('Invalid ticket')
        # Pop first: a wrong sender/identity attempt invalidates the ticket.
        entry=self._tickets.pop(token,None)
        if entry is None:
            raise Denied('Missing, expired, or already used ticket')
        expected, deadline=entry
        if self._clock() >= deadline:
            raise Denied('Expired ticket')
        if not hmac.compare_digest(repr(expected),repr(intent)):
            raise Denied('Caller or device identity changed')
        return True

    def invalidate_all(self):
        self._tickets.clear()
