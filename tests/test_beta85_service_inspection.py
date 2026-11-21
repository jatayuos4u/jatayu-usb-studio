import unittest
from unittest.mock import AsyncMock
from beta56_secure_dispatch import Envelope
from beta85_service_inspection import inspect_device
from sender_identity import SenderIdentity

S=':1.234'
D='/dev/sdb'
GOOD={'device':D,'candidate':True,'status':'ADVISORY_ONLY','reasons':[],
      'dependencies':['sdb'],'writing_enabled':False}

def env(device=D, sender=S, signature='s', member='InspectDevice', body=None):
    return Envelope(sender, member, signature, (device,) if body is None else body)

class Beta85ServiceTests(unittest.IsolatedAsyncioTestCase):
    async def call(self, e=None, identity=None, result=None):
        resolver=AsyncMock(return_value=identity if identity is not None else SenderIdentity(S,1000,1234))
        inspector=lambda d: GOOD if result is None else result
        return await inspect_device(object(), e or env(), resolver=resolver, inspector=inspector)
    async def test_advisory_never_authorizes(self):
        r=await self.call()
        self.assertTrue(r['ok']); self.assertFalse(r['authorized'])
        self.assertFalse(r['writing_enabled']); self.assertEqual(r['device_inspection']['status'],'ADVISORY_ONLY')
    async def test_bad_sender(self):
        self.assertFalse((await self.call(env(sender='org.fake')) )['ok'])
    async def test_wrong_method(self):
        self.assertFalse((await self.call(env(member='RequestWrite')))['ok'])
    async def test_wrong_signature(self):
        self.assertFalse((await self.call(env(signature='')))['ok'])
    async def test_bad_path(self):
        for path in ('/dev/../sda','/tmp/disk','/dev/sdb/part','/dev/sdb\n'):
            self.assertFalse((await self.call(env(device=path)))['ok'])
    async def test_bad_body(self):
        self.assertFalse((await self.call(env(body=())))['ok'])
    async def test_mismatch_credentials(self):
        self.assertFalse((await self.call(identity=SenderIdentity(':1.5',1000,1234)))['ok'])
    async def test_bad_pid(self):
        self.assertFalse((await self.call(identity=SenderIdentity(S,1000,0)))['ok'])
    async def test_bad_inspection(self):
        self.assertFalse((await self.call(result=dict(GOOD,writing_enabled=True)))['ok'])
    async def test_bad_status(self):
        self.assertFalse((await self.call(result=dict(GOOD,status='AUTHORIZED')))['ok'])
    async def test_blocked_evidence(self):
        r=await self.call(result=dict(GOOD,status='BLOCKED',candidate=False,reasons=['mounted']))
        self.assertTrue(r['ok']);self.assertFalse(r['device_inspection']['candidate'])
    async def test_inspector_failure(self):
        async def resolver(*a): return SenderIdentity(S,1000,1234)
        def failure(*a): raise RuntimeError('unavailable')
        r=await inspect_device(object(),env(),resolver=resolver,inspector=failure)
        self.assertFalse(r['ok'])

if __name__=='__main__': unittest.main()
