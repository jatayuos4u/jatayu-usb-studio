import asyncio
import unittest
from unittest.mock import patch
from beta65_polkit import check_polkit_inspection, ACTION

class Bus:
    def __init__(self, reply=None, error=None):
        self.reply, self.error, self.calls = reply, error, []
    async def call(self, message):
        self.calls.append(message)
        if self.error: raise self.error
        return self.reply

class Polkit65Tests(unittest.TestCase):
    def test_invalid_sender_rejected_without_bus_call(self):
        bus=Bus()
        self.assertFalse(asyncio.run(check_polkit_inspection(bus, 'org.example.Forged')))
        self.assertEqual(bus.calls, [])
    def test_missing_authority_denied(self):
        self.assertFalse(asyncio.run(check_polkit_inspection(Bus(), ':1.12')))
    def test_transport_error_denied(self):
        self.assertFalse(asyncio.run(check_polkit_inspection(Bus(error=RuntimeError('offline')), ':1.12')))
    def test_bad_timeout_denied(self):
        self.assertFalse(asyncio.run(check_polkit_inspection(Bus(), ':1.12', timeout=100)))
    def test_write_action_not_used(self):
        self.assertEqual(ACTION, 'in.jatayuos.usbstudio.inspect')
        self.assertNotIn('write', ACTION)
    def test_no_write_capability_exposed(self):
        import beta65_polkit
        self.assertFalse(hasattr(beta65_polkit, 'write_device'))
