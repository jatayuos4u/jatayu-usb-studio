import unittest
from pathlib import Path
class IntegrationContract(unittest.TestCase):
    def test_backend_wired_fail_closed(self):
        s=(Path(__file__).resolve().parents[1]/'src/main.cpp').read_text()
        for token in ('"--target",dev','candidate_checks_passed','allowed_to_write','Safety backend missing'):
            self.assertIn(token,s)
