import importlib.util
import json
from pathlib import Path
import tempfile
import subprocess
import sys
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / 'scripts/redact_logs.py'
spec = importlib.util.spec_from_file_location('redact_logs', SCRIPT)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

class RedactionTests(unittest.TestCase):
    def test_structured_and_mule_encoded(self):
        event = {'correlationId': '25d25946-246b-47f0-92c9-5d77b11fbbf4', 'availableQuantity': '100000', 'status': 502, 'email': 'alice@example.com', 'payload': {'diagnosis': 'private'}, 'message': 'Alice lives nearby'}
        for text in [json.dumps(event), json.dumps(json.dumps(event)), 'timestamp INFO demo.events - ' + json.dumps(json.dumps(event))]:
            out = json.loads(module.Redactor().line(text))
            self.assertEqual(out, {key: event[key] for key in ['correlationId', 'availableQuantity', 'status']})

    def test_patterns_and_nested_keys(self):
        r = module.Redactor('patterns', ['customId'])
        value = r.value({'payload': {'name': 'Alice', 'email': 'a@example.com', 'customId': 'private-id'}, 'message': 'a@example.com Bearer abc.def 192.168.1.1 +44 7700 900123 SW1A 1AA'})
        serialized = json.dumps(value)
        for secret in ['a@example.com', 'abc.def', '192.168.1.1', '7700', 'SW1A', 'private-id', 'Alice']:
            self.assertNotIn(secret, serialized)
        self.assertNotIn('Alice', module.Redactor().line(json.dumps({'name':'Alice'})))

    def test_unstructured_default_is_omitted(self):
        self.assertEqual(module.Redactor().line('Alice has a medical condition\n'), '[OMITTED:unstructured_line]\n')

    def test_cli_preserves_source_permissions_and_refuses_overwrite(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / 'input.log'
            original = 'email=alice@example.com\n-----BEGIN PRIVATE KEY-----\nsecret\n-----END PRIVATE KEY-----\n'
            source.write_text(original)
            args = [sys.executable, str(SCRIPT), str(source), '--mode', 'patterns']
            subprocess.run(args, check=True, capture_output=True)
            target = source.with_name('input.redacted.log')
            self.assertNotIn('secret', target.read_text())
            self.assertNotIn('alice', target.read_text())
            self.assertEqual(source.read_text(), original)
            self.assertEqual(target.stat().st_mode & 0o777, 0o600)
            self.assertNotEqual(subprocess.run(args, capture_output=True).returncode, 0)

if __name__ == '__main__':
    unittest.main()
