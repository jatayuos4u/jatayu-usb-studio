import pathlib, unittest
SOURCE = pathlib.Path(__file__).resolve().parents[1] / "src/main.cpp"
class Beta30DeviceConsistency(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.code=SOURCE.read_text()
    def test_common_lsblk_schema(self):
        self.assertIn('static QStringList usbLsblkArguments()',self.code)
        self.assertGreaterEqual(self.code.count('usbLsblkArguments()'),4)
    def test_common_partition_counter(self):
        self.assertIn('static int usbPartitionCount(',self.code)
        self.assertIn('usbPartitionCount(disk)',self.code)
        self.assertIn('usbPartitionCount(d)',self.code)
    def test_identity_recheck(self):
        self.assertIn('usbIdentity(disk)!=expectedIdentity',self.code)
    def test_read_only(self):
        self.assertIn('Physical USB repair, partitioning and formatting are DISABLED.',self.code)
if __name__=='__main__': unittest.main()
