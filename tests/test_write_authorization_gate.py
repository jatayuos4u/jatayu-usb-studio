import unittest
from dataclasses import replace
from write_authorization_gate import WriteIntent, DryRunGate, GateRejected, validate_intent, execute_write


def valid():
    return WriteIntent('a'*64, 1024, '/dev/sdb', 'SERIAL123', '8:16', 4096, 1000, ':1.45')


class GateTests(unittest.TestCase):
    def test_valid(self): self.assertTrue(validate_intent(valid()))
    def test_invalid_digest(self):
        with self.assertRaises(GateRejected): validate_intent(replace(valid(), iso_sha256='z'*64))
    def test_insufficient_capacity(self):
        with self.assertRaises(GateRejected): validate_intent(replace(valid(), device_size_bytes=100))
    def test_missing_serial(self):
        with self.assertRaises(GateRejected): validate_intent(replace(valid(), serial=''))
    def test_untrusted_sender(self):
        with self.assertRaises(GateRejected): validate_intent(replace(valid(), caller_bus_name='org.example.Fake'))
    def test_partition_path(self):
        with self.assertRaises(GateRejected): validate_intent(replace(valid(), destination='/dev/disk/by-id/abc'))
    def test_confirmation_is_not_authorization(self):
        gate=DryRunGate(clock=lambda: 0)
        r=gate.prepare(valid())
        self.assertFalse(r['writing_enabled'])
        final=gate.confirm(valid(),r['challenge'])
        self.assertFalse(final['authorized'])
        self.assertFalse(final['writing_enabled'])
    def test_changed_destination_rejected(self):
        gate=DryRunGate(clock=lambda: 0)
        r=gate.prepare(valid())
        with self.assertRaises(GateRejected): gate.confirm(replace(valid(), destination='/dev/sdc'),r['challenge'])
    def test_expiry(self):
        now=[0]
        gate=DryRunGate(clock=lambda: now[0], lifetime_seconds=10)
        r=gate.prepare(valid()); now[0]=10
        with self.assertRaises(GateRejected): gate.confirm(valid(),r['challenge'])
    def test_replay(self):
        gate=DryRunGate(clock=lambda: 0)
        r=gate.prepare(valid()); gate.confirm(valid(),r['challenge'])
        with self.assertRaises(GateRejected): gate.confirm(valid(),r['challenge'])
    def test_failed_attempt_consumes_challenge(self):
        gate=DryRunGate(clock=lambda: 0)
        r=gate.prepare(valid())
        with self.assertRaises(GateRejected): gate.confirm(replace(valid(), serial='different'),r['challenge'])
        with self.assertRaises(GateRejected): gate.confirm(valid(),r['challenge'])
    def test_execute_always_denied(self):
        with self.assertRaises(GateRejected): execute_write(valid())

if __name__ == '__main__': unittest.main()
