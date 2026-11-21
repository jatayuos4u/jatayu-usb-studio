import unittest
from sender_identity import validate_unique_name, SenderIdentity, authorization_decision

class Beta18IdentityTests(unittest.TestCase):
    def test_unique_sender(self): self.assertTrue(validate_unique_name(':1.42'))
    def test_well_known_rejected(self): self.assertFalse(validate_unique_name('org.example.Service'))
    def test_injection_rejected(self): self.assertFalse(validate_unique_name(':1.42;evil'))
    def test_empty_rejected(self): self.assertFalse(validate_unique_name(''))
    def test_nonstring_rejected(self): self.assertFalse(validate_unique_name(12))
    def test_missing_components_rejected(self): self.assertFalse(validate_unique_name(':1'))
    def test_all_flags_denied(self):
        self.assertFalse(authorization_decision(SenderIdentity(':1.42',1000,200),True)['authorized'])
    def test_no_identity_denied(self):
        self.assertFalse(authorization_decision(None,True)['writing_enabled'])
    def test_service_still_has_no_write_method(self):
        from pathlib import Path
        s=(Path(__file__).resolve().parent.parent/'system_service.py').read_text()
        self.assertNotIn('def Write(',s)
