import unittest
from dataclasses import replace
from beta64_authorization import Denied
from beta76_trusted_preflight import DeviceSnapshot
from beta79_integrated_inspection import inspect, request_write

BASE = DeviceSnapshot('/dev/sdb','8:16','/sys/devices/mock',4096000,True,False,False,False,True)
def topology(d):
    return dict(device=d, dependencies=('sdb','sdb1'), removable=True,
                read_only=False,mounted=False,system_disk=False,writing_enabled=False)
class IntegrationTests(unittest.TestCase):
    def run_inspection(self, snapshot=lambda d: BASE, topo=topology):
        return inspect('/dev/sdb',snapshot_fn=snapshot,topology_fn=topo)
    def test_clean_is_only_advisory(self):
        r=self.run_inspection();self.assertTrue(r.candidate);self.assertFalse(r.writing_enabled)
    def test_changed_identity(self):
        calls=iter([BASE,replace(BASE,major_minor='8:32')])
        r=self.run_inspection(snapshot=lambda d:next(calls));self.assertFalse(r.candidate)
        self.assertIn('changed',r.reasons[0])
    def test_mounted(self): self.assertFalse(self.run_inspection(snapshot=lambda d:replace(BASE,mounted=True)).candidate)
    def test_internal(self): self.assertFalse(self.run_inspection(snapshot=lambda d:replace(BASE,removable=False)).candidate)
    def test_system_disk(self): self.assertFalse(self.run_inspection(snapshot=lambda d:replace(BASE,system_disk=True)).candidate)
    def test_read_only(self): self.assertFalse(self.run_inspection(snapshot=lambda d:replace(BASE,read_only=True)).candidate)
    def test_partition(self): self.assertFalse(self.run_inspection(snapshot=lambda d:replace(BASE,whole_disk=False)).candidate)
    def test_topology_denial(self):
        def bad(d):raise Denied('Mounted storage dependency')
        self.assertIn('Mounted',self.run_inspection(topo=bad).reasons[0])
    def test_mismatch(self):
        def bad(d):return dict(topology(d),mounted=True)
        self.assertFalse(self.run_inspection(topo=bad).candidate)
    def test_no_dependencies(self):
        self.assertFalse(self.run_inspection(topo=lambda d:dict(topology(d),dependencies=())).candidate)
    def test_no_write_flag(self):
        self.assertFalse(self.run_inspection(topo=lambda d:dict(topology(d),writing_enabled=True)).candidate)
    def test_missing_device(self):self.assertFalse(inspect('bad').candidate)
    def test_no_writes(self):
        with self.assertRaises(Denied):request_write('/dev/sdb')
