import asyncio
import unittest
from types import SimpleNamespace
from beta56_secure_dispatch import Envelope, dispatch, from_dbus_message, MAX_BODY_BYTES

class Beta56Tests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.calls = []
        async def resolve(bus, sender):
            self.calls.append(('resolve', sender))
            return SimpleNamespace(unique_name=sender, uid=1000, pid=1234)
        async def polkit(bus, sender):
            self.calls.append(('polkit', sender))
            return True
        self.resolve = resolve
        self.polkit = polkit

    async def check(self, env, **kw):
        return await dispatch(None, env, identity_resolver=kw.get('resolver', self.resolve),
                              permission_checker=kw.get('polkit', self.polkit))

    async def test_valid_capabilities_remains_nonwriting(self):
        result = await self.check(Envelope(':1.4', 'Capabilities', '', ()))
        self.assertTrue(result['sender_verified'])
        self.assertFalse(result['writing_enabled'])
        self.assertFalse(result['authorized'])
    async def test_inspection_permission_not_write_grant(self):
        result = await self.check(Envelope(':1.4', 'InspectAuthorization', '', ()))
        self.assertTrue(result['inspection_permission'])
        self.assertFalse(result['authorized'])
    async def test_write_denied_even_with_valid_sender(self):
        result = await self.check(Envelope(':1.4', 'RequestWrite', 's', ('/dev/sdb',)))
        self.assertFalse(result['writing_enabled'])
        self.assertEqual(self.calls, [])
    async def test_forged_sender_rejected(self):
        result = await self.check(Envelope('org.fake.Service', 'Capabilities', '', ()))
        self.assertFalse(result['ok'])
    async def test_wrong_signature_rejected(self):
        self.assertFalse((await self.check(Envelope(':1.4', 'Capabilities', 's', ())))['ok'])
    async def test_unexpected_body_rejected(self):
        self.assertFalse((await self.check(Envelope(':1.4', 'Capabilities', '', ('x',))))['ok'])
    async def test_oversized_write_denied(self):
        result = await self.check(Envelope(':1.4', 'RequestWrite', 's', ('x' * (MAX_BODY_BYTES+1),)))
        self.assertFalse(result['ok'])
    async def test_mismatched_credentials_rejected(self):
        async def wrong(bus, sender): return SimpleNamespace(unique_name=':1.99', uid=1000, pid=123)
        self.assertFalse((await self.check(Envelope(':1.4', 'Capabilities', '', ()), resolver=wrong))['ok'])
    async def test_invalid_pid_rejected(self):
        async def bad(bus, sender): return SimpleNamespace(unique_name=sender, uid=1000, pid=0)
        self.assertFalse((await self.check(Envelope(':1.4', 'Capabilities', '', ()), resolver=bad))['ok'])
    async def test_resolver_error_denied(self):
        async def fail(bus, sender): raise PermissionError('no creds')
        self.assertFalse((await self.check(Envelope(':1.4', 'Capabilities', '', ()), resolver=fail))['ok'])
    async def test_polkit_exception_fails_closed(self):
        async def fail(bus, sender): raise RuntimeError('polkit down')
        result = await self.check(Envelope(':1.4', 'InspectAuthorization', '', ()), polkit=fail)
        self.assertFalse(result['inspection_permission'])
    async def test_polkit_nonboolean_fails_closed(self):
        async def strange(bus, sender): return 1
        result = await self.check(Envelope(':1.4', 'InspectAuthorization', '', ()), polkit=strange)
        self.assertFalse(result['inspection_permission'])
    async def test_non_envelope_denied(self):
        self.assertFalse((await self.check({'sender': ':1.4'}))['ok'])
    async def test_envelope_transport_fields_only(self):
        msg = SimpleNamespace(sender=':1.4', member='Capabilities', signature='', body=[], uid=0)
        env = from_dbus_message(msg)
        self.assertEqual(env.sender, ':1.4')
        self.assertEqual(env.body, ())
