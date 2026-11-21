import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
class DeploymentTests(unittest.TestCase):
    def test_unit_unprivileged(self):
        t=(ROOT/'packaging/systemd/jatayu-usb-inspection-beta69.service').read_text()
        self.assertIn('User=jatayu-usb-preview',t)
        self.assertIn('PrivateDevices=yes',t)
        self.assertNotIn('ExecStart=/bin/sh',t)
    def test_install_is_opt_in(self):
        t=(ROOT/'beta69_install_inspection.sh').read_text()
        self.assertNotIn('^systemctl start',t)
        self.assertNotIn('^systemctl enable',t)
        self.assertNotIn('systemctl restart dbus',t)
    def test_only_inspection_dependencies_installed(self):
        t=(ROOT/'beta69_install_inspection.sh').read_text()
        self.assertNotIn('beta59_experimental_writer',t)
        self.assertNotIn('privileged_service.py',t)
    def test_polkit_denied_by_default(self):
        t=(ROOT/'packaging/polkit/in.jatayuos.usbstudio.inspect.policy').read_text()
        self.assertIn('<allow_active>no</allow_active>',t)
