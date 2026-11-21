import pathlib,unittest
ROOT=pathlib.Path(__file__).resolve().parents[1]
class Beta27ChecksumUITests(unittest.TestCase):
 def test_file_picker(self):
  self.assertIn('Checksum file…',(ROOT/'src/main.cpp').read_text())
 def test_bare_and_named_checksums(self):
  s=(ROOT/'src/main.cpp').read_text();self.assertIn('bareLine',s);self.assertIn('sumLine',s)
 def test_ambiguous_rejected(self):
  self.assertIn('matches.size()!=1',(ROOT/'src/main.cpp').read_text())
 def test_no_claim_of_authenticity(self):
  self.assertIn('publisher authenticity not established',(ROOT/'src/main.cpp').read_text())
 def test_writing_disabled(self):
  self.assertIn('writing remains disabled',(ROOT/'src/main.cpp').read_text())
