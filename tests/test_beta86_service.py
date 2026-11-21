import asyncio
import unittest
from unittest.mock import patch
from beta86_service_inspection import InspectionLimiter
from beta85_service_inspection import inspect_device
from beta56_secure_dispatch import Envelope
from sender_identity import SenderIdentity

class Beta86Tests(unittest.IsolatedAsyncioTestCase):
    async def test_busy_rejected(self):
        lim=InspectionLimiter(workers=1)
        try:
            lim.active=1
            with self.assertRaises(RuntimeError): await lim.inspect('/dev/sdb')
        finally: lim.close()

    async def test_closed_rejected(self):
        lim=InspectionLimiter(workers=1); lim.close()
        with self.assertRaises(RuntimeError): await lim.inspect('/dev/sdb')

    async def test_async_inspector(self):
        async def resolver(bus,sender): return SenderIdentity(sender,1000,1234)
        async def inspector(device):
            return {'device':device,'candidate':True,'status':'ADVISORY_ONLY',
                    'reasons':[],'dependencies':['sdb'],'writing_enabled':False}
        e=Envelope(':1.23','InspectDevice','s',('/dev/sdb',))
        r=await inspect_device(object(),e,resolver=resolver,inspector=inspector)
        self.assertTrue(r['ok']); self.assertFalse(r['authorized'])

    async def test_async_failure_closed(self):
        async def resolver(bus,sender): return SenderIdentity(sender,1000,1234)
        async def inspector(device): raise RuntimeError('unavailable')
        e=Envelope(':1.23','InspectDevice','s',('/dev/sdb',))
        r=await inspect_device(object(),e,resolver=resolver,inspector=inspector)
        self.assertFalse(r['ok'])

if __name__ == '__main__': unittest.main()
