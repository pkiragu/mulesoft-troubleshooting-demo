"""Synthetic fixture only: verifies exported Mule events are sanitized."""
import importlib.util
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('redact', ROOT/'scripts/redact_logs.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

class CredentialRedactionTests(unittest.TestCase):
    def test_synthetic_credentials_in_mule_log(self):
        secret = 'DEMO_ONLY_NOT_A_REAL_SECRET_inventory_2026'
        event = {'event': 'backend.request', 'correlationId': 'leak-demo-001',
                 'headers': {'client_id': 'demo-inventory-client', 'client_secret': secret}}
        for mode in ['strict', 'patterns']:
            for line in [json.dumps(event), 'INFO demo.events - ' + json.dumps(json.dumps(event))]:
                r = module.Redactor(mode)
                output = r.line(line)
                self.assertNotIn(secret, output)
                self.assertIn('leak-demo-001', output)
                self.assertIn('backend.request', output)
                self.assertTrue(r.counts)
