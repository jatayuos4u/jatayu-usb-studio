import unittest
from beta64_authorization import Denied
from beta75_writer_authorization import AuthorizationBoundary, VerifiedContext

GOOD = VerifiedContext(':1.45', 1000, '8:16', '/sys/devices/pci0000:00/usb1', 'a'*64, 1024)
class BoundaryTests(unittest.TestCase):
    def test_default_fails_closed(self):
        with self.assertRaises(Denied): AuthorizationBoundary().prepare({}, observed_sender=':1.45')
    def test_missing_sender_denied(self):
        with self.assertRaises(Denied): AuthorizationBoundary(verifier=lambda a,b:GOOD).prepare({}, observed_sender='')
    def test_invalid_verifier_output_denied(self):
        with self.assertRaises(Denied): AuthorizationBoundary(verifier=lambda a,b:True).prepare({}, observed_sender=':1.45')
    def test_sender_mismatch_denied(self):
        with self.assertRaises(Denied): AuthorizationBoundary(verifier=lambda a,b:GOOD).prepare({}, observed_sender=':1.46')
    def test_verified_context_is_structured(self):
        self.assertEqual(AuthorizationBoundary(verifier=lambda a,b:GOOD).prepare({}, observed_sender=':1.45').uid,1000)
    def test_no_ticket_even_with_verifier(self):
        with self.assertRaises(Denied): AuthorizationBoundary(verifier=lambda a,b:GOOD).request_ticket({}, observed_sender=':1.45')
    def test_no_physical_write(self):
        with self.assertRaises(Denied): AuthorizationBoundary().request_write('/dev/sdb')
    def test_status_never_claims_writer(self):
        self.assertFalse(AuthorizationBoundary().status()['writing_enabled'])
    def test_bad_identity_denied(self):
        bad=VerifiedContext(':1.45',1000,'8:16','/tmp/fake','a'*64,1024)
        with self.assertRaises(Denied): AuthorizationBoundary(verifier=lambda a,b:bad).prepare({}, observed_sender=':1.45')
