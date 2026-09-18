#!/usr/bin/env python3
"""Offline log minimization. No network, dependencies, or in-place writes."""
import argparse
from collections import Counter
import json
import os
from pathlib import Path
import re

# Only fields used for diagnostic analysis in this demo. Values still get scanned.
ALLOWED = set('timestamp synthetic event api release correlationId storeId sku quantity availableQuantity orderId status errorType durationMs elapsedMs stockType expectedType actualType'.lower().split())
SENSITIVE = re.compile(r'password|passwd|secret|token|authorization|cookie|api.?key|email|phone|mobile|address|postcode|postal|first.?name|last.?name|full.?name|customer|user.?id|date.?of.?birth|dob|passport|national|ssn|credit|card|iban|medical|health|religion|ethnicity|biometric', re.I)
PATTERNS = [
    ('private_key', re.compile(r'-----BEGIN [^-]*PRIVATE KEY-----.*?-----END [^-]*PRIVATE KEY-----', re.S)),
    ('credential', re.compile(r'\b(?:Bearer|Basic)\s+[A-Za-z0-9+/_.=~-]+', re.I)),
    ('jwt', re.compile(r'\beyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\b')),
    ('email', re.compile(r'(?<![\w.+-])[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}\b')),
    ('ipv4', re.compile(r'\b(?:\d{1,3}\.){3}\d{1,3}\b')),
    ('ipv6', re.compile(r'(?<![\w:])(?:[0-9a-f]{0,4}:){2,}[0-9a-f:]{0,39}(?![\w:])', re.I)),
    ('uk_postcode', re.compile(r'\b[A-Z]{1,2}\d[A-Z\d]?\s+\d[A-Z]{2}\b', re.I)),
    ('uk_ni', re.compile(r'\b[A-CEGHJ-PR-TW-Z]{2}\s?\d{2}\s?\d{2}\s?\d{2}\s?[A-D]\b', re.I)),
    ('ssn', re.compile(r'\b\d{3}-\d{2}-\d{4}\b')),
    ('iban', re.compile(r'\b[A-Z]{2}\d{2}(?: ?[A-Z0-9]){11,30}\b')),
    ('long_number', re.compile(r'(?<![\w-])(?:\d[ -]?){13,19}(?![\w-])')),
    ('phone', re.compile(r'(?<![\w-])(?:\+\d[\d ().-]{7,}\d|0\d[\d ()-]{7,}\d)(?![\w-])')),
    ('home_path', re.compile(r'(?:/Users/|/home/)[^/\s"\\]+|[A-Z]:\\Users\\[^\\\s"]+', re.I)),
]
ASSIGNMENT = re.compile(r'(?P<key>[\w.-]*(?:password|passwd|secret|token|authorization|cookie|api[_-]?key|email|phone|address|name|customerId|userId)[\w.-]*)\s*[:=]\s*(?:"[^"\n]*"|\'[^\'\n]*\'|[^\s,;&}]+)', re.I)

class Redactor:
    def __init__(self, mode='strict', extra_keys=()):
        self.mode = mode
        self.extra_keys = {key.lower() for key in extra_keys}
        self.counts = Counter()

    def replace(self, category):
        self.counts[category] += 1
        return '[REDACTED:' + category + ']'

    def text(self, value):
        for category, pattern in PATTERNS:
            value = pattern.sub(lambda match: self.replace(category), value)
        return ASSIGNMENT.sub(lambda match: match['key'] + '=' + self.replace('sensitive_field'), value)

    def value(self, value):
        if isinstance(value, dict):
            out = {}
            for key, child in value.items():
                if SENSITIVE.search(key) or key.lower() in {'name', 'username', 'ip', 'ipaddress'} or key.lower() in self.extra_keys:
                    self.counts['sensitive_field'] += 1
                    # Omit key names too; dynamic keys can themselves contain personal data.
                elif self.mode == 'strict' and key.lower() not in ALLOWED:
                    self.counts['unapproved_field'] += 1
                else:
                    out[self.text(key)] = self.value(child)
            return out
        if isinstance(value, list):
            return [self.value(child) for child in value]
        if isinstance(value, str):
            try:
                decoded = json.loads(value)
            except (ValueError, RecursionError):
                return self.text(value)
            if isinstance(decoded, (dict, list)):
                return json.dumps(self.value(decoded), ensure_ascii=False)
            return self.text(value)
        return value

    def line(self, line):
        # Includes JSONL, double-encoded JSON, and Mule's prefixed JSON messages.
        candidates = [line.strip()]
        if ' - ' in line:
            candidates.append(line.split(' - ', 1)[1].strip())
        for candidate in candidates:
            try:
                data = json.loads(candidate)
                for _ in range(3):
                    if not isinstance(data, str):
                        break
                    data = json.loads(data)
                if isinstance(data, (dict, list)):
                    return json.dumps(self.value(data), ensure_ascii=False) + '\n'
            except (ValueError, RecursionError):
                pass
        if not line.strip():
            return '\n'
        if self.mode == 'strict':
            self.counts['unstructured_line'] += 1
            return '[OMITTED:unstructured_line]\n'
        return self.text(line)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('input', type=Path)
    parser.add_argument('--output', type=Path, help='New file; existing files are never overwritten')
    parser.add_argument('--mode', choices=['strict', 'patterns'], default='strict')
    parser.add_argument('--redact-key', action='append', default=[], help='Additional JSON key to omit; repeatable')
    args = parser.parse_args()
    output = args.output or args.input.with_name(args.input.stem + '.redacted' + args.input.suffix)
    report = output.with_name(output.name + '.report.json')
    if output.resolve() == args.input.resolve() or output.exists() or report.exists():
        parser.error('Choose a new output path; input and existing output/report files are never overwritten.')
    redactor = Redactor(args.mode, args.redact_key)
    # Read strictly: invalid UTF-8 fails rather than silently losing evidence.
    source = args.input.read_text(encoding='utf-8')
    # Remove multi-line private keys before line processing.
    source = PATTERNS[0][1].sub(lambda match: redactor.replace('private_key'), source)
    result = ''.join(redactor.line(line) for line in source.splitlines(keepends=True))
    summary = {'mode': args.mode, 'input_lines': len(source.splitlines()),
               'redactions': dict(sorted(redactor.counts.items())),
               'review_required': True,
               'note': 'Heuristic minimization, not a guarantee of anonymization or GDPR compliance. Review before sharing. Counts contain no matched values.'}
    output.parent.mkdir(parents=True, exist_ok=True)
    for path, content in [(output, result), (report, json.dumps(summary, indent=2) + '\n')]:
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, 'w', encoding='utf-8') as stream:
            stream.write(content)
    print(f'Sanitized log: {output}\nCount-only report: {report}\nReview the sanitized file before sharing.')

if __name__ == '__main__':
    main()
