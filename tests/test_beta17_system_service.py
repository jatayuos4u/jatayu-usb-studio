import json
import pathlib
import unittest
from system_service import capabilities, reject_request, BUS_NAME

ROOT = pathlib.Path(__file__).resolve().parents[1]
class Beta17SystemServiceTests(unittest.TestCase):
    def test_capabilities_nonwriting(self):
        self.assertIs(capabilities()['writing_enabled'], False)
    def test_no_polkit_claim(self):
        self.assertIs(capabilities()['polkit_enabled'], False)
    def test_nonprivileged(self):
        self.assertIs(capabilities()['privileged'], False)
    def test_request_denied(self):
        self.assertIs(reject_request('anything')['authorized'], False)
    def test_service_has_no_write_method(self):
        s=(ROOT/'system_service.py').read_text()
        self.assertNotIn('def Write(',s)
        self.assertNotIn('open(',s)
    def test_system_bus_explicit(self):
        self.assertIn('BusType.SYSTEM',(ROOT/'system_service.py').read_text())
    def test_bus_config_ownership_restricted(self):
        s=(ROOT/'packaging/system-bus/in.jatayuos.USBStudio.Inspection.conf').read_text()
        self.assertIn('policy user="jatayu-usb-preview"',s)
        self.assertNotIn('<allow own="*"',s)
    def test_not_autostarted(self):
        self.assertFalse(any('WantedBy=multi-user.target' in f.read_text() for f in (ROOT/'packaging').rglob('*.service')))
