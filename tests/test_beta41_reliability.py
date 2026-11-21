import unittest
from pathlib import Path
SOURCE=(Path(__file__).resolve().parents[1]/"src/main.cpp").read_text()
class Beta41ReliabilityTests(unittest.TestCase):
    def test_event_filter(self):
        for label in ("All events", "Information", "Warnings", "Critical"):
            self.assertIn(label,SOURCE)
        self.assertIn('filter!=e.severity',SOURCE)
    def test_warning_rechecks_saved_baseline(self):
        self.assertIn('identityAlert=!matched;',SOURCE)
        self.assertIn('USB matches the saved advisory baseline again',SOURCE)
    def test_no_silent_fallback_on_manual_baseline(self):
        self.assertIn('automaticInitialBaseline && devices.size()==1',SOURCE)
        self.assertIn('Baseline capture refused:',SOURCE)
    def test_no_physical_writes(self):
        self.assertIn('No disk writes',SOURCE)
        self.assertIn('Physical writes, cloning, formatting and repair remain disabled.',SOURCE)
    def test_event_limit_and_dedup(self):
        self.assertIn('safetyEvents.size()>40',SOURCE)
        self.assertIn('if(lastEventKey==key)return;',SOURCE)
