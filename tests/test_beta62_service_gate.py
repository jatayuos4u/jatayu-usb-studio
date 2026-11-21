import unittest
from beta62_service_gate import ServiceState, dispatch, readiness

class TestServiceGate(unittest.TestCase):
    def test_defaults_deny(self):
        r = dispatch('GetReadiness')
        self.assertFalse(r['writing_enabled'])
        self.assertFalse(r['write_authorized'])
        self.assertFalse(r['ready_for_review'])
    def test_write_method_denied(self):
        for method in ('WriteUSB', 'RequestWrite', 'Format', 'EraseDisk'):
            self.assertFalse(dispatch(method)['ok'])
    def test_arguments_denied(self):
        self.assertFalse(dispatch('GetReadiness', ['/dev/sdb'])['ok'])
    def test_partial_state_denied(self):
        r = readiness(ServiceState(polkit_verified=True, sender_verified=True))
        self.assertFalse(r['ready_for_review'])
        self.assertFalse(r['write_authorized'])
    def test_even_all_checks_do_not_authorize(self):
        r = readiness(ServiceState(*([True] * 6)))
        self.assertTrue(r['ready_for_review'])
        self.assertFalse(r['write_authorized'])
        self.assertFalse(r['writing_enabled'])
