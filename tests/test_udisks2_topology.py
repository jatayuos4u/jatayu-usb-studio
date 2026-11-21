import copy
import json
import subprocess
import unittest
from udisks2_backend import inspect_usb, DeviceRejected

BASE = {'blockdevices':[{'name':'/dev/sdb','type':'disk','tran':'usb','rm':True,
    'ro':False,'size':31029460992,'mountpoints':[None],
    'children':[{'name':'/dev/sdb1','type':'part','mountpoints':[None]}]}]}

def run_for(data, code=0):
    def run(args, **kwargs):
        assert args[0] == 'lsblk' and '--json' in args
        return subprocess.CompletedProcess(args,code,json.dumps(data),'')
    return run

class TestReadOnlyTopology(unittest.TestCase):
    def test_unmounted_usb(self):
        out=inspect_usb('/dev/sdb',runner=run_for(BASE))
        self.assertEqual(out['status'],'READ_ONLY_INSPECTED')
        self.assertFalse(out['authorized'])
        self.assertFalse(out['writing_enabled'])
    def test_reject_mounted_child(self):
        d=copy.deepcopy(BASE);d['blockdevices'][0]['children'][0]['mountpoints']=['/media/usb']
        with self.assertRaises(DeviceRejected):inspect_usb('/dev/sdb',runner=run_for(d))
    def test_reject_internal(self):
        d=copy.deepcopy(BASE);d['blockdevices'][0]['tran']='sata'
        with self.assertRaises(DeviceRejected):inspect_usb('/dev/sdb',runner=run_for(d))
    def test_reject_nonremovable(self):
        d=copy.deepcopy(BASE);d['blockdevices'][0]['rm']=False
        with self.assertRaises(DeviceRejected):inspect_usb('/dev/sdb',runner=run_for(d))
    def test_reject_unknown_mounts(self):
        d=copy.deepcopy(BASE);d['blockdevices'][0]['mountpoints']=None
        with self.assertRaises(DeviceRejected):inspect_usb('/dev/sdb',runner=run_for(d))
    def test_reject_readonly(self):
        d=copy.deepcopy(BASE);d['blockdevices'][0]['ro']=True
        with self.assertRaises(DeviceRejected):inspect_usb('/dev/sdb',runner=run_for(d))
    def test_reject_ambiguous_topology(self):
        d=copy.deepcopy(BASE);d['blockdevices'].append(copy.deepcopy(d['blockdevices'][0]))
        with self.assertRaises(DeviceRejected):inspect_usb('/dev/sdb',runner=run_for(d))
    def test_reject_invalid_json(self):
        def bad(args,**kw):return subprocess.CompletedProcess(args,0,'{bad','')
        with self.assertRaises(DeviceRejected):inspect_usb('/dev/sdb',runner=bad)
    def test_reject_partition_input(self):
        with self.assertRaises(ValueError):inspect_usb('/dev/sdb1',runner=run_for(BASE))
    def test_reject_failed_command(self):
        with self.assertRaises(DeviceRejected):inspect_usb('/dev/sdb',runner=run_for(BASE,1))
