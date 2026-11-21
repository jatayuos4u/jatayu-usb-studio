import unittest
from beta84_inspection_cli import combine

DEVICE='/dev/sdb'
LOCAL={'device':DEVICE,'candidate':True,'reasons':[],'dependencies':['sdb'], 'writing_enabled':False,'status':'ADVISORY_ONLY'}
SERVICE={'ok':True,'real_system_bus':True,'status':'INSPECTION_ONLY','writing_enabled':False}

class Beta84Tests(unittest.TestCase):
    def test_service_is_not_device_authority(self):
        r=combine(DEVICE,LOCAL,SERVICE)
        self.assertTrue(r['service_verified'])
        self.assertFalse(r['trusted_device_inspection'])
        self.assertFalse(r['writing_enabled'])
        self.assertEqual(r['inspection_source'],'local_unprivileged')
    def test_no_service_still_local_advisory(self):
        r=combine(DEVICE,LOCAL,{'status':'NOT_INSTALLED_OR_INACTIVE','ok':False})
        self.assertEqual(r['status'],'ADVISORY_ONLY')
        self.assertFalse(r['service_verified'])
    def test_bad_local_data_fails_closed(self):
        for value in (None,{},dict(LOCAL,writing_enabled=True),dict(LOCAL,device='/dev/sda'),dict(LOCAL,reasons='')):
            with self.subTest(value=value):
                r=combine(DEVICE,value,SERVICE)
                self.assertFalse(r['candidate'])
                self.assertEqual(r['status'],'UNAVAILABLE')
    def test_blocked_remains_blocked(self):
        r=combine(DEVICE,dict(LOCAL,candidate=False,status='BLOCKED',reasons=['mounted']),SERVICE)
        self.assertEqual(r['status'],'BLOCKED')
        self.assertIn('mounted',r['reasons'])
    def test_false_service_claims(self):
        for s in ({'ok':True,'status':'INSPECTION_ONLY','writing_enabled':False},
                  {'ok':True,'real_system_bus':True,'status':'INSPECTION_ONLY','writing_enabled':True},
                  None):
            self.assertFalse(combine(DEVICE,LOCAL,s)['service_verified'])
    def test_contradictory_local(self):
        r=combine(DEVICE,dict(LOCAL,status='BLOCKED'),SERVICE)
        self.assertEqual(r['status'],'BLOCKED')
    def test_source_never_certified(self):
        r=combine(DEVICE,LOCAL,SERVICE)
        self.assertNotIn('trusted',r['inspection_source'])

if __name__=='__main__':unittest.main()
