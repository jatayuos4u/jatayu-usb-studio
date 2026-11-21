import unittest
from pathlib import Path
from unittest.mock import patch
import live_inspection_cli as cli

ROOT=Path(__file__).resolve().parents[1]
class Beta13Integration(unittest.TestCase):
    def test_failure_is_non_authorizing(self):
        with patch.object(cli, 'inspect_device', side_effect=ValueError('replaced')):
            report=cli.inspect('/dev/sdb')
        self.assertFalse(report['ok'])
        self.assertFalse(report['writing_authorized'])
    def test_success_still_never_authorizes(self):
        class F:
            major=8; minor=16; size_bytes=123
        with patch.object(cli, 'inspect_device', return_value=F()), patch.object(cli, 'inspect_usage', return_value={'safe_snapshot':True}):
            report=cli.inspect('/dev/sdb')
        self.assertTrue(report['ok'])
        self.assertFalse(report['writing_authorized'])
    def test_gui_requires_both_inspections(self):
        source=(ROOT/'src/main.cpp').read_text()
        self.assertIn('passed=passed && livePassed',source)
        self.assertIn('live_inspection_cli.py',source)
    def test_installer_includes_live_dependencies(self):
        cm=(ROOT/'CMakeLists.txt').read_text()
        for name in ('live_inspection_cli.py','device_revalidation.py','live_safety.py'):
            self.assertIn(name,cm)
