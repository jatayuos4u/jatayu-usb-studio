import unittest
from unittest.mock import AsyncMock, patch
from beta56_secure_dispatch import Envelope
from beta66_inspection_service import inspect_dispatch, PolkitInspectionService
from beta63_service import InspectionService

class TestBeta66(unittest.IsolatedAsyncioTestCase):
    async def test_real_polkit_checker_is_wired(self):
        with patch('beta66_inspection_service.dispatch', new_callable=AsyncMock) as call:
            call.return_value={'writing_enabled':False}
            env=Envelope(':1.42','InspectAuthorization','',())
            result=await inspect_dispatch(object(),env)
            self.assertFalse(result['writing_enabled'])
            self.assertEqual(call.await_args.kwargs['permission_checker'].__name__,
                             'check_polkit_inspection')

    async def test_denied_request_write(self):
        env=Envelope(':1.42','RequestWrite','s',('{}',))
        result=await inspect_dispatch(object(),env)
        self.assertFalse(result['authorized'])
        self.assertFalse(result['writing_enabled'])

    async def test_invalid_sender_denied(self):
        env=Envelope('spoofed','InspectAuthorization','',())
        result=await inspect_dispatch(object(),env)
        self.assertFalse(result['authorized'])

    async def test_invalid_signature_denied(self):
        env=Envelope(':1.42','InspectAuthorization','s',('bad',))
        result=await inspect_dispatch(object(),env)
        self.assertFalse(result['authorized'])

    async def test_service_uses_lifecycle(self):
        self.assertTrue(issubclass(PolkitInspectionService,InspectionService))

    async def test_polkit_failure_denied(self):
        from beta65_polkit import check_polkit_inspection
        self.assertFalse(await check_polkit_inspection(None, 'invalid'))
