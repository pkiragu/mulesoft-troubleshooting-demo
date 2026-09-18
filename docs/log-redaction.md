# Sanitize logs locally before analysis

Run from the repository root with Python 3. No packages, API keys, AI model or network connection are required. Originals are left untouched; output and its count-only report are created with owner-only file permissions. Existing files are never overwritten.

```sh
python3 scripts/redact_logs.py evidence/runtime/mule-console.log --output .run/sanitized/mule-console.redacted.log
```

Default `strict` mode reads JSON/JSONL, JSON encoded inside strings, and Mule ` - ` prefixed JSON events. It keeps only the diagnostic field allowlist in the script, scans their string values, drops other fields, and replaces unstructured lines with omission markers. This intentionally removes free-text exception messages and stack traces. Stock values retain their number/string types so the demo incident remains diagnosable.

When stack traces are needed, select the less restrictive mode explicitly:

```sh
python3 scripts/redact_logs.py evidence/runtime/mule-console.log --mode patterns --output .run/sanitized/mule-console.patterns.log
```

Pattern mode retains unstructured text and unknown JSON fields. It removes sensitive keyed JSON fields and matches common email, phone, IP, UK postcode/NI, US SSN, IBAN, long account/card-like numbers, credentials, JWTs, private keys and local home-directory usernames. Patterns can both miss sensitive values and redact harmless text. Structured sensitive fields include addresses, names, customer identifiers, health and other sensitive categories. Add custom JSON field names with repeated `--redact-key employeeReference` options.

Neither mode can reliably recognize all names, addresses, sensitive narratives, encoded data or organization-specific identifiers. Even allowlisted fields can contain personal information. This is a review aid, not certification of anonymization or GDPR compliance. Correlation IDs, order IDs, store IDs and timestamps are intentionally retained for troubleshooting; they may be linkable to people in real environments. To omit these structured fields, use e.g. `--redact-key correlationId --redact-key orderId`. In pattern mode these options do not remove identifiers from arbitrary prose.

Before providing evidence for analysis:

1. Run the script against a local copy of the downloaded log.
2. Review the sanitized output and `.report.json` counts locally. The report never includes matched values.
3. Check retained messages and identifiers for context-specific personal information. Use strict mode or omit additional fields when uncertain.
4. Provide only the reviewed redacted file, not the source log or a folder containing both.

Generated files under `.run/` are git-ignored. No files are uploaded automatically.

Tests: `python3 -m unittest discover -s tests -p 'test_redact_logs.py'`.
