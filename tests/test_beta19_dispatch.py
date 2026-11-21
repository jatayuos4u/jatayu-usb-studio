import asyncio
import unittest
from sender_identity import SenderIdentity
from sender_dispatch import inspect_sender_request

class Beta19DispatchTests(unittest.TestCase):
    def run_check(self, sender=':1.42', payload='{}', resolver=None):
        async def good(bus, name): return SenderIdentity(name, 1000, 1234)
        return asyncio.run(inspect_sender_request(object(), sender, payload, resolver=resolver or good))
    def test_valid_sender_still_denied(self): self.assertFalse(self.run_check()['authorized'])
    def test_valid_sender_no_write(self): self.assertFalse(self.run_check()['writing_enabled'])
    def test_oversize_denied(self): self.assertFalse(self.run_check(payload='x'*20000)['authorized'])
    def test_nonstring_denied(self): self.assertFalse(self.run_check(payload=42)['authorized'])
    def test_spoofed_identity_denied(self):
        async def spoof(bus, name): return SenderIdentity(':1.999',1000,1234)
        self.assertIn('Untrusted', self.run_check(resolver=spoof)['reason'])
    def test_bool_uid_denied(self):
        async def bad(bus, name): return SenderIdentity(name,True,1234)
        self.assertFalse(self.run_check(resolver=bad)['authorized'])
    def test_missing_pid_denied(self):
        async def bad(bus, name): return SenderIdentity(name,1000,0)
        self.assertIn('Invalid',self.run_check(resolver=bad)['reason'])
    def test_bus_failure_denied(self):
        async def bad(bus, name): raise PermissionError('failed')
        self.assertFalse(self.run_check(resolver=bad)['authorized'])
    def test_no_write_method(self):
        from pathlib import Path
        s=(Path(__file__).resolve().parents[1]/'system_service.py').read_text()
        self.assertNotIn('def Write(',s)
    def test_transport_envelope_used(self):
        from pathlib import Path
        s=(Path(__file__).resolve().parents[1]/'system_service.py').read_text()
        self.assertIn('msg.sender',s)
        self.assertIn('add_message_handler',s)
