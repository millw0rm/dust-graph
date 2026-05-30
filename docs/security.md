# Security and Sensitive Data Handling

## Purpose

Dust Graph ingestion must preserve useful dependency, ownership, and traceability facts without retaining sensitive source material. Collectors, parsers, normalizers, and graph writers must treat source data as untrusted and potentially secret-bearing until it has passed redaction and minimization checks.

## Core Rules

1. **Never store raw secrets.** Do not persist raw secrets, access tokens, refresh tokens, API keys, passwords, passphrases, private keys, certificates with private key material, session cookies, credential blobs, or full connection strings.
2. **Store only redacted connection metadata.** Connection evidence may be represented by safe metadata such as provider type, engine, protocol, host category, port, database or resource name when safe, variable name, secret reference name, and redaction reason. Credential-bearing user info, passwords, tokens, query parameters, and full URLs must be removed or tokenized before storage.
3. **Hash or redact usernames when configured.** Usernames, service account names, email addresses, and principal identifiers must be hashed or redacted when collector or tenant configuration requires identity minimization. Hashes should use a configured salt or tenant-scoped keyed hash so values remain useful for correlation without exposing raw identifiers.
4. **Keep source references for traceability.** Every ingested fact should retain source references such as repository, file path, line range, commit SHA, cluster, namespace, API endpoint, collector name, extraction timestamp, and confidence when available. Source references must point to evidence locations without embedding sensitive raw values.
5. **Record evidence IDs instead of raw logs where possible.** For logs, events, alerts, tickets, and packet or flow records, store stable evidence IDs, event IDs, rule IDs, summary counters, timestamps, and redacted labels instead of full raw log lines or payloads whenever possible.
6. **Support environment tags.** Ingested records should support environment tags such as `prod`, `staging`, and `dev` so graph consumers can distinguish production exposure from non-production evidence. Unknown or custom environments should be represented as explicit configured tags rather than inferred from secret values.
7. **Require allowlists for sensitive repository patterns.** Repository collectors must use explicit allowlists for file patterns that may contain sensitive content, such as `.env`, `*.tfvars`, kubeconfig files, private key paths, generated secrets, or local configuration files. Files outside the allowlist must be skipped or scanned only for safe metadata approved by policy.
8. **Plan for pluggable redaction policies.** Redaction should be policy-driven so future deployments can plug in tenant-specific detectors, allowlists, hashing rules, field-level retention rules, and compliance controls without changing collector core logic.

## Ingestion Workflow Requirements

- Run secret detection and field classification before graph persistence.
- Prefer structured references such as secret names, key names, variable names, resource addresses, and dependency types over source values.
- Attach a redaction record when a value is removed, including the source reference, field name or path, policy name, reason, and detector confidence when available.
- Fail closed for ambiguous high-risk fields: if a collector cannot determine that a field is safe, it must redact or skip the value.
- Keep raw source data only in transient memory or short-lived processing storage required for extraction, and do not include raw sensitive values in errors, debug logs, metrics, traces, or test fixtures.

## Examples of Safe Representation

```yaml
connection:
  type: postgres
  source_ref: config/prod.env:12
  environment: prod
  metadata:
    variable_name: DATABASE_URL
    host_category: managed-database
    port: 5432
    database_name: payments
  redactions:
    - field: username
      action: hash
      reason: configured identity minimization
    - field: password
      action: redact
      reason: credential-bearing connection string
    - field: raw_connection_string
      action: drop
      reason: full connection strings are not stored
```

```yaml
evidence:
  evidence_id: logevt:payments-api:2026-05-30:8f4d2a
  source_ref: cloudwatch:/aws/ecs/payments-api
  environment: prod
  summary: redacted authentication failure count
  raw_log_stored: false
```
