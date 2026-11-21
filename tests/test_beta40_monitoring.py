import pathlib
import unittest

SOURCE = (pathlib.Path(__file__).resolve().parents[1] / "src/main.cpp").read_text()

class Beta40Monitoring(unittest.TestCase):
    def test_event_history_bounded(self):
        self.assertIn("while(safetyEvents.size()>40)", SOURCE)
    def test_monitoring_read_only(self):
        self.assertIn("refreshTimer.start(2500)", SOURCE)
        self.assertIn("Physical writes, cloning, formatting and repair remain disabled.", SOURCE)
    def test_latched_warning(self):
        self.assertIn("identityAlert=!matched;", SOURCE)
    def test_session_history(self):
        self.assertIn("DEVICE SAFETY EVENT HISTORY", SOURCE)
        self.assertIn("USB disconnected or no removable USB detected", SOURCE)
    def test_dialog_conditional(self):
        self.assertIn("identityAlert ?", SOURCE)
