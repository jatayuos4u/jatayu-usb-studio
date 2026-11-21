import tempfile
import shutil
import unittest
from pathlib import Path
from backend_security_review import ROOT, review

class Beta45BackendReviewTests(unittest.TestCase):
    def test_current_source_passes_static_review(self):
        self.assertEqual(review(), [])

    def copy(self):
        temp = tempfile.TemporaryDirectory()
        target = Path(temp.name)
        for name in ('system_service.py', 'sender_dispatch.py', 'sender_identity.py',
                     'polkit_inspection.py', 'service_security.py', 'privileged_service.py'):
            shutil.copy2(ROOT/name, target/name)
        shutil.copytree(ROOT/'packaging', target/'packaging')
        return temp, target

    def test_unexpected_bus_method_fails(self):
        temp, root = self.copy()
        with temp:
            p = root/'system_service.py'
            p.write_text(p.read_text().replace("('Capabilities', 'Prepare')", "('Capabilities', 'Prepare', 'Write')"))
            self.assertTrue(any('allowlist' in s for s in review(root)))

    def test_removed_sender_binding_fails(self):
        temp, root = self.copy()
        with temp:
            p = root/'system_service.py'
            p.write_text(p.read_text().replace('msg.sender', "':1.999'"))
            self.assertTrue(any('sender envelope' in s for s in review(root)))

    def test_subprocess_in_service_fails(self):
        temp, root = self.copy()
        with temp:
            p = root/'system_service.py'
            p.write_text(p.read_text()+'\nimport subprocess\nsubprocess.run(["true"])\n')
            self.assertTrue(any('disallowed' in s for s in review(root)))

    def test_polkit_interactive_flag_fails(self):
        temp, root = self.copy()
        with temp:
            p = root/'polkit_inspection.py'
            p.write_text(p.read_text().replace("ACTION_ID, {}, 0, ''", "ACTION_ID, {}, 1, ''"))
            self.assertTrue(any('noninteractive' in s for s in review(root)))

    def test_root_service_fails(self):
        temp, root = self.copy()
        with temp:
            p = root/'packaging/systemd/jatayu-usb-inspection.service'
            p.write_text(p.read_text().replace('User=jatayu-usb-preview','User=root'))
            self.assertTrue(any('deployment' in s for s in review(root)))
