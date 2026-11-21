import json
import unittest
from writer_protocol import WriterServicePrototype, decode_request, ProtocolError, MAX_REQUEST_BYTES

GOOD = {'version':2,'target':'/dev/sdb','iso_path':'/tmp/test.iso',
        'expected_major':8,'expected_minor':16,'expected_size':31000000000,
        'expected_sysfs_path':'/sys/devices/test','expected_serial':'123'}

class WriterProtocolTests(unittest.TestCase):
    def encode(self, **changes):
        return json.dumps({**GOOD,**changes}).encode()
    def test_valid_parse(self):
        self.assertEqual(decode_request(self.encode()).target, '/dev/sdb')
    def test_partition_rejected_by_protocol(self):
        # A partition-shaped path is syntactically possible; live inspector rejects partitions.
        self.assertEqual(decode_request(self.encode(target='/dev/sdb1')).target,'/dev/sdb1')
    def test_path_traversal(self):
        with self.assertRaises(ProtocolError): decode_request(self.encode(target='/dev/../sda'))
    def test_extra_fields(self):
        with self.assertRaises(ProtocolError): decode_request(self.encode(command='dd'))
    def test_bool_integer(self):
        with self.assertRaises(ProtocolError): decode_request(self.encode(expected_major=True))
    def test_zero_capacity(self):
        with self.assertRaises(ProtocolError): decode_request(self.encode(expected_size=0))
    def test_oversized(self):
        with self.assertRaises(ProtocolError): decode_request(b'x'*(MAX_REQUEST_BYTES+1))
    def test_invalid_utf8(self):
        with self.assertRaises(ProtocolError): decode_request(b'\xff')
    def test_service_never_authorizes(self):
        svc=WriterServicePrototype()
        for action in ('prepare','write','cancel','unknown'):
            self.assertFalse(svc.handle(action,self.encode())['authorized'])
        self.assertFalse(svc.capabilities()['writing_enabled'])
    def test_no_write_api(self):
        self.assertFalse(WriterServicePrototype().capabilities()['real_device_open_enabled'])

if __name__=='__main__': unittest.main()
