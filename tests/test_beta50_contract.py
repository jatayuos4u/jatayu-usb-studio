import unittest
from privileged_write_service_contract import PhysicalWriteServiceContract

class TestBeta50Contract(unittest.TestCase):
    def setUp(self): self.service = PhysicalWriteServiceContract()
    def test_no_system_service(self): self.assertFalse(self.service.capabilities()["system_bus_service_installed"])
    def test_no_polkit(self): self.assertFalse(self.service.capabilities()["polkit_authorization_enabled"])
    def test_no_physical_writes(self): self.assertFalse(self.service.capabilities()["physical_write_enabled"])
    def test_reject_prepare(self): self.assertFalse(self.service.prepare(b"{}")["authorized"])
    def test_reject_write(self): self.assertFalse(self.service.write(b"{}")["authorized"])
    def test_reject_cancel(self): self.assertFalse(self.service.cancel()["ok"])
