import asyncio
import unittest
from unittest.mock import patch
from sender_identity import SenderIdentity
from sender_dispatch import inspect_sender_request
from polkit_inspection import check_inspection_permission, ACTION_ID

class Beta20PolkitTests(unittest.TestCase):
    def run_dispatch(self, checker):
        async def identity(bus, sender): return SenderIdentity(sender, 1000, 4567)
        return asyncio.run(inspect_sender_request(object(), ':1.52', '{"version":1,"action":"inspect","device":"/dev/sdb"}', resolver=identity, permission_checker=checker))

    def test_polkit_denial(self):
        async def check(bus, sender): return False
        self.assertIn('denied', self.run_dispatch(check)['reason'])
    def test_polkit_approval_never_writes(self):
        async def check(bus, sender): return True
        r=self.run_dispatch(check)
        self.assertFalse(r['authorized']); self.assertFalse(r['writing_enabled'])
    def test_polkit_exception_fails_closed(self):
        async def check(bus, sender): raise RuntimeError('service gone')
        self.assertFalse(self.run_dispatch(check)['authorized'])
    def test_invalid_sender_skips_polkit(self):
        self.assertFalse(asyncio.run(check_inspection_permission(object(),'org.fake.Service')))
    def test_missing_polkit_service(self):
        class Bus:
            async def call(self, msg): raise OSError('missing')
        self.assertFalse(asyncio.run(check_inspection_permission(Bus(),':1.52')))
    def test_polkit_request_is_noninteractive(self):
        from pathlib import Path
        s=(Path(__file__).resolve().parents[1]/'polkit_inspection.py').read_text()
        self.assertIn("ACTION_ID, {}, 0, ''",s)
        self.assertIn("'system-bus-name'",s)
    def test_action_is_inspection_only(self):
        self.assertEqual(ACTION_ID,'in.jatayuos.usbstudio.inspect')
    def test_no_write_method(self):
        from pathlib import Path
        s=(Path(__file__).resolve().parents[1]/'system_service.py').read_text()
        self.assertNotIn('def Write(',s)
    def test_identity_is_transport_bound(self):
        from pathlib import Path
        s=(Path(__file__).resolve().parents[1]/'system_service.py').read_text()
        self.assertIn('msg.sender',s)
    def test_no_root_installation(self):
        from pathlib import Path
        self.assertNotIn('pkexec', (Path(__file__).resolve().parents[1]/'system_service.py').read_text())
