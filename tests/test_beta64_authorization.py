import unittest
from dataclasses import replace
from beta64_authorization import WriteIntent, TicketStore, Denied

I=WriteIntent(':1.20',1000,'8:16','/sys/devices/pci0000:00/usb1/1-2','a'*64,1435871232)

class TicketTests(unittest.TestCase):
    def setUp(self):
        self.now=[100.0]
        self.store=TicketStore(clock=lambda:self.now[0])
    def test_default_denial(self):
        with self.assertRaises(Denied): self.store.issue(I)
    def test_single_use(self):
        t=self.store.issue(I,polkit_authorized=True)
        self.assertTrue(self.store.consume(t,I))
        with self.assertRaises(Denied): self.store.consume(t,I)
    def test_expired(self):
        t=self.store.issue(I,polkit_authorized=True);self.now[0]+=30
        with self.assertRaises(Denied):self.store.consume(t,I)
    def test_sender_mismatch_invalidates(self):
        t=self.store.issue(I,polkit_authorized=True)
        with self.assertRaises(Denied):self.store.consume(t,replace(I,sender=':1.21'))
        with self.assertRaises(Denied):self.store.consume(t,I)
    def test_uid_mismatch(self):
        t=self.store.issue(I,polkit_authorized=True)
        with self.assertRaises(Denied):self.store.consume(t,replace(I,uid=0))
    def test_device_mismatch(self):
        t=self.store.issue(I,polkit_authorized=True)
        with self.assertRaises(Denied):self.store.consume(t,replace(I,device_major_minor='8:32'))
    def test_iso_mismatch(self):
        t=self.store.issue(I,polkit_authorized=True)
        with self.assertRaises(Denied):self.store.consume(t,replace(I,iso_sha256='b'*64))
    def test_invalidate_all(self):
        t=self.store.issue(I,polkit_authorized=True);self.store.invalidate_all()
        with self.assertRaises(Denied):self.store.consume(t,I)
    def test_invalid_uid_bool(self):
        with self.assertRaises(Denied):replace(I,uid=True).validate()
    def test_invalid_checksum(self):
        with self.assertRaises(Denied):replace(I,iso_sha256='xyz').validate()
    def test_invalid_sender(self):
        with self.assertRaises(Denied):replace(I,sender='org.fake').validate()
    def test_invalid_size(self):
        with self.assertRaises(Denied):replace(I,iso_size=0).validate()
    def test_ttl_limit(self):
        with self.assertRaises(ValueError):TicketStore(ttl=120)
    def test_false_polkit(self):
        with self.assertRaises(Denied):self.store.issue(I,polkit_authorized=1)
if __name__=='__main__':unittest.main()
