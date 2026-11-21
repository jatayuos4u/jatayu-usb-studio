import json
import subprocess
import unittest
from unittest.mock import patch
import beta55_resource_audit as audit

class Beta55ResourceAuditTests(unittest.TestCase):
    def test_failure_on_resource_warning(self):
        fake = subprocess.CompletedProcess([], 0, '{"ok":true}', 'ResourceWarning: unclosed socket')
        with patch.object(audit.subprocess, 'run', return_value=fake):
            with self.assertRaisesRegex(RuntimeError, 'cleanup audit failed'):
                audit.audit()

    def test_failure_on_authorization(self):
        fake = subprocess.CompletedProcess([], 0, json.dumps({"ok": True, "private_bus": True, "calls": 3, "authorized": True, "writing_enabled": False}), '')
        with patch.object(audit.subprocess, 'run', return_value=fake):
            with self.assertRaisesRegex(RuntimeError, 'unexpected security result'):
                audit.audit()

    def test_missing_dependency_not_false_pass(self):
        fake = subprocess.CompletedProcess([], 1, '', 'ModuleNotFoundError: dbus_next')
        with patch.object(audit.subprocess, 'run', return_value=fake):
            with self.assertRaisesRegex(RuntimeError, 'cleanup audit failed'):
                audit.audit()

    def test_valid_probe_pair(self):
        outputs = [subprocess.CompletedProcess([], 0, json.dumps({"ok": True, "private_bus": True, "calls": 3, "writing_enabled": False, "authorized": False}), ''),
                   subprocess.CompletedProcess([], 0, json.dumps({"ok": True, "private_bus": True, "negative_cases": 6, "writing_enabled": False}), '')]
        with patch.object(audit.subprocess, 'run', side_effect=outputs):
            result = audit.audit()
        self.assertEqual(result['private_bus_probes'], 2)
        self.assertFalse(result['writing_enabled'])
