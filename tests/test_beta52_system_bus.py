import asyncio
import unittest
from unittest.mock import patch, AsyncMock
import beta52_system_bus as svc

class TestBeta52(unittest.TestCase):
    def run_handle(self, method, signature='', body=None, sender=':1.44'):
        return asyncio.run(svc.handle(method, signature, [] if body is None else body, sender, object()))
    def test_capabilities_denies_writes(self):
        result=self.run_handle('Capabilities')
        self.assertFalse(result['writing_enabled'])
        self.assertFalse(result['privileged_backend'])
    def test_request_write_denied(self):
        result=self.run_handle('RequestWrite','s',['{"authorized":true}'])
        self.assertFalse(result['authorized'])
        self.assertFalse(result['writing_enabled'])
    def test_wrong_signature_denied(self):
        self.assertFalse(self.run_handle('RequestWrite','',[])['authorized'])
    def test_bad_sender_denied(self):
        self.assertFalse(self.run_handle('Capabilities',sender='fake')['authorized'])
    def test_unknown_method_denied(self):
        self.assertFalse(self.run_handle('EraseDisk')['authorized'])
    def test_extra_args_denied(self):
        self.assertFalse(self.run_handle('Capabilities','',['unexpected'])['authorized'])
    def test_polkit_positive_never_grants_writing(self):
        with patch.object(svc,'check_inspection_permission',new=AsyncMock(return_value=True)):
            result=self.run_handle('InspectAuthorization')
        self.assertTrue(result['inspection_permission'])
        self.assertFalse(result['authorized'])
        self.assertFalse(result['writing_enabled'])
    def test_polkit_negative(self):
        with patch.object(svc,'check_inspection_permission',new=AsyncMock(return_value=False)):
            result=self.run_handle('InspectAuthorization')
        self.assertFalse(result['inspection_permission'])
        self.assertFalse(result['authorized'])
