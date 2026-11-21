import unittest
from privileged_service_boundary import WriteBoundary
from privileged_write_state_machine import SimulatedWriteJob, Stage

class Beta51BoundaryTests(unittest.TestCase):
    def test_capabilities_denied(self):
        self.assertFalse(WriteBoundary().capabilities()["physical_writes_enabled"])
    def test_sender_claim_cannot_authorize(self):
        self.assertFalse(WriteBoundary().prepare(b"{}", sender=":1.1", polkit_result=True)["authorized"])
    def test_execution_denied(self):
        self.assertFalse(WriteBoundary().execute()["writing_enabled"])
    def test_reject_invalid_sizes(self):
        for size in (-1, 0, True, 2**64):
            with self.subTest(size=size), self.assertRaises(ValueError): SimulatedWriteJob(size)
    def test_job_initial_state(self):
        job = SimulatedWriteJob(1024)
        self.assertEqual(job.snapshot().stage, "idle")
        self.assertFalse(job.snapshot().writing_enabled)
    def test_prepared_state(self):
        job = SimulatedWriteJob(1024)
        self.assertEqual(job.prepare().stage, "prepared")
    def test_no_fake_progress(self):
        job = SimulatedWriteJob(1024); job.prepare()
        with self.assertRaises(PermissionError): job.simulate_progress(10)
    def test_cancel(self):
        job = SimulatedWriteJob(1024); job.prepare()
        self.assertEqual(job.cancel().stage, Stage.CANCELLED.value)
    def test_no_cancel_twice(self):
        job = SimulatedWriteJob(1024); job.cancel()
        with self.assertRaises(ValueError): job.cancel()
    def test_fail(self):
        job = SimulatedWriteJob(1024)
        self.assertEqual(job.fail().stage, "failed")
