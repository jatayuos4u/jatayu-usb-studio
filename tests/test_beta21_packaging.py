import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from shutil import copytree
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from packaging_audit import audit_templates

class Beta21PackagingTests(unittest.TestCase):
    def test_templates_pass(self): self.assertEqual(audit_templates(), [])
    def test_policy_default_deny(self):
        s = (ROOT/'packaging/polkit/in.jatayuos.usbstudio.inspect.policy').read_text()
        self.assertEqual(s.count('>no</allow_'), 3)
    def test_no_write_action(self):
        s = (ROOT/'packaging/polkit/in.jatayuos.usbstudio.inspect.policy').read_text()
        self.assertNotIn('usbstudio.write', s)
    def test_dedicated_account(self):
        s = (ROOT/'packaging/systemd/jatayu-usb-inspection.service').read_text()
        self.assertIn('User=jatayu-usb-preview',s)
    def test_no_auto_enable(self):
        s = (ROOT/'packaging/systemd/jatayu-usb-inspection.service').read_text()
        self.assertNotIn('WantedBy=multi-user.target',s)
    def test_no_privileged_caps(self):
        s = (ROOT/'packaging/systemd/jatayu-usb-inspection.service').read_text()
        self.assertIn('CapabilityBoundingSet=\n',s)
    def test_private_devices(self):
        s = (ROOT/'packaging/systemd/jatayu-usb-inspection.service').read_text()
        self.assertIn('PrivateDevices=yes',s)
    def test_tampered_policy_fails(self):
        with TemporaryDirectory() as tmp:
            base = Path(tmp); copytree(ROOT/'packaging',base/'packaging')
            f=base/'packaging/polkit/in.jatayuos.usbstudio.inspect.policy'
            f.write_text(f.read_text().replace('<allow_active>no</allow_active>','<allow_active>yes</allow_active>'))
            self.assertTrue(audit_templates(base))
    def test_tampered_unit_fails(self):
        with TemporaryDirectory() as tmp:
            base=Path(tmp);copytree(ROOT/'packaging',base/'packaging')
            f=base/'packaging/systemd/jatayu-usb-inspection.service'
            f.write_text(f.read_text().replace('PrivateDevices=yes','PrivateDevices=no'))
            self.assertTrue(audit_templates(base))
    def test_no_write_api(self):
        s=(ROOT/'system_service.py').read_text()
        self.assertNotIn("msg.member == 'Write'",s)
