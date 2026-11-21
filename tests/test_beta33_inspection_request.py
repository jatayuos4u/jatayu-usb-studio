import asyncio
import json
import unittest
from inspection_request import parse_inspection_request, InvalidInspectionRequest, denied_response
from sender_dispatch import inspect_sender_request

GOOD = '{"version":1,"action":"inspect","device":"/dev/sdb"}'

class FakeIdentity:
    unique_name = ':1.44'
    uid = 1000
    pid = 1234

async def resolver(bus, sender):
    return FakeIdentity()

async def allow(bus, sender):
    return True

class InspectionRequestTests(unittest.TestCase):
    def test_valid(self): self.assertEqual(parse_inspection_request(GOOD)['device'], '/dev/sdb')
    def test_capabilities(self): self.assertEqual(parse_inspection_request('{"version":1,"action":"capabilities","device":"/dev/sdb"}')['action'], 'capabilities')
    def test_non_string(self):
        with self.assertRaises(InvalidInspectionRequest): parse_inspection_request(None)
    def test_oversized(self):
        with self.assertRaises(InvalidInspectionRequest): parse_inspection_request('x'*4097)
    def test_malformed(self):
        with self.assertRaises(InvalidInspectionRequest): parse_inspection_request('{')
    def test_array(self):
        with self.assertRaises(InvalidInspectionRequest): parse_inspection_request('[]')
    def test_unknown_field(self):
        with self.assertRaises(InvalidInspectionRequest): parse_inspection_request(GOOD[:-1]+',"uid":0}')
    def test_boolean_version(self):
        with self.assertRaises(InvalidInspectionRequest): parse_inspection_request(GOOD.replace('1,','true,'))
    def test_write_action(self):
        with self.assertRaises(InvalidInspectionRequest): parse_inspection_request(GOOD.replace('inspect','write_iso'))
    def test_partition(self):
        with self.assertRaises(InvalidInspectionRequest): parse_inspection_request(GOOD.replace('/dev/sdb','/dev/sdb1'))
    def test_path_traversal(self):
        with self.assertRaises(InvalidInspectionRequest): parse_inspection_request(GOOD.replace('/dev/sdb','/dev/../sda'))
    def test_deny(self):
        self.assertFalse(denied_response()['writing_enabled'])
    def test_dispatch_valid_still_denies(self):
        result=asyncio.run(inspect_sender_request(None, ':1.44', GOOD, resolver=resolver, permission_checker=allow))
        self.assertFalse(result['authorized']); self.assertFalse(result['writing_enabled'])
    def test_dispatch_write_denied(self):
        result=asyncio.run(inspect_sender_request(None, ':1.44', GOOD.replace('inspect','format_usb'), resolver=resolver, permission_checker=allow))
        self.assertFalse(result['authorized']); self.assertFalse(result['writing_enabled'])
