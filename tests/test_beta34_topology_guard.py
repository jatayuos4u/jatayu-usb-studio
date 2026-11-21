import copy
import json
import unittest
from device_topology_guard import inspect_topology

BASE = {'blockdevices':[{'name':'sdb','path':'/dev/sdb','type':'disk','tran':'usb','rm':True,'ro':False,'size':32000000000,'pkname':None,'mountpoints':[None], 'children':[{'path':'/dev/sdb1','type':'part','mountpoints':[None]}]}]}

def check(d, target='/dev/sdb'):
    return inspect_topology(json.dumps(d), target)

class TopologyGuardTests(unittest.TestCase):
    def test_clean(self):
        r=check(BASE); self.assertTrue(r['ok']); self.assertEqual(r['partition_count'],1); self.assertFalse(r['authorized']); self.assertFalse(r['writing_enabled'])
    def test_missing(self): self.assertFalse(check(BASE,'/dev/sdc')['ok'])
    def test_duplicate(self):
        d=copy.deepcopy(BASE); d['blockdevices'].append(copy.deepcopy(d['blockdevices'][0])); self.assertFalse(check(d)['ok'])
    def test_internal(self):
        d=copy.deepcopy(BASE); d['blockdevices'][0]['tran']='sata'; self.assertFalse(check(d)['ok'])
    def test_nonremovable(self):
        d=copy.deepcopy(BASE); d['blockdevices'][0]['rm']=False; self.assertFalse(check(d)['ok'])
    def test_mounted_partition(self):
        d=copy.deepcopy(BASE); d['blockdevices'][0]['children'][0]['mountpoints']=['/home']; self.assertFalse(check(d)['ok'])
    def test_mounted_disk(self):
        d=copy.deepcopy(BASE); d['blockdevices'][0]['mountpoints']=['/']; self.assertFalse(check(d)['ok'])
    def test_unknown_mount(self):
        d=copy.deepcopy(BASE); del d['blockdevices'][0]['children'][0]['mountpoints']; self.assertFalse(check(d)['ok'])
    def test_partition_target(self): self.assertFalse(check(BASE,'/dev/sdb1')['ok'])
    def test_readonly(self):
        d=copy.deepcopy(BASE); d['blockdevices'][0]['ro']=True; self.assertFalse(check(d)['ok'])
    def test_unknown_size(self):
        d=copy.deepcopy(BASE); d['blockdevices'][0]['size']='32G'; self.assertFalse(check(d)['ok'])
    def test_complex_topology(self):
        d=copy.deepcopy(BASE); d['blockdevices'][0]['children'][0]['type']='crypt'; self.assertFalse(check(d)['ok'])
    def test_bad_json(self): self.assertFalse(inspect_topology('{','/dev/sdb')['ok'])
    def test_oversized(self): self.assertFalse(inspect_topology(' ' * (1024*1024+1),'/dev/sdb')['ok'])
    def test_invalid_path(self): self.assertFalse(check(BASE,'/dev/../sdb')['ok'])
    def test_no_authorization_on_success(self):
        r=check(BASE); self.assertIs(r['authorized'],False); self.assertIs(r['writing_enabled'],False)
