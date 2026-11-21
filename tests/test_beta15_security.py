import unittest
from service_security import Caller, validate_caller, prepare_authorization, capabilities

class Beta15SecurityTests(unittest.TestCase):
    def test_no_caller(self):
        self.assertFalse(validate_caller(None))
    def test_bool_uid_rejected(self):
        self.assertFalse(validate_caller(Caller(True, 123, True)))
    def test_invalid_pid(self):
        self.assertFalse(validate_caller(Caller(1000, 0, True)))
    def test_unauthenticated(self):
        self.assertFalse(validate_caller(Caller(1000, 123, False)))
    def test_valid_caller_not_authorization(self):
        self.assertTrue(validate_caller(Caller(1000, 123, True)))
        self.assertFalse(prepare_authorization(Caller(1000, 123, True))["authorized"])
    def test_all_flags_still_denied(self):
        report = prepare_authorization(Caller(1000, 123, True), polkit_result=True,
            live_identity=True, no_holders=True, image_verified=True)
        self.assertFalse(report["authorized"])
        self.assertFalse(report["writing_enabled"])
    def test_no_privileged_capability(self):
        self.assertFalse(capabilities()["writing_enabled"])
        self.assertFalse(capabilities()["polkit_enabled"])
