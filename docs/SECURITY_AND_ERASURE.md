# Security boundary and deletion claims

## Current status: public demo only

The Hugging Face Space is an unauthenticated public demo. It uses synthetic fixtures and should receive only synthetic or already-public benchmark data. Do not upload real customer conversations, confidential company data, passwords, API keys, bearer tokens, cloud keys, or other credentials.

The upload route rejects common credential field names and recognizable token formats. This is an accidental-upload warning layer, not a data-loss-prevention product. It can miss secrets, personal information, proprietary content, encoded data, and new token formats. It must not be used to justify uploading sensitive material.

Visitor cookies scope demo uploads and reports; Clear my data and the 30-minute inactivity worker remove the app's visitor files. HTTP responses are marked `Cache-Control: no-store`, with basic browser security headers. These measures do not authenticate a company user, encrypt app files, erase infrastructure backups, or prove that every copy is unrecoverable. A browser cookie is not company identity or tenant authorization.

## Credentials are not benchmark data

Never place credentials in JSON/JSONL benchmark files or model prompts. A company integration should obtain a narrowly scoped, read-only, short-lived credential at runtime from the company's secret manager or workload identity. Keep it server-side, restrict it to a staging tenant, rotate it, and prevent it from appearing in request/exception logs or evaluation reports. The benchmark should contain test identities and expected behavior, not reusable credentials.

## Requirements before real company data

Run a separate, private, single-tenant deployment in the company's cloud account or network. Do not turn the public Hugging Face Space into the data plane for customer information. At minimum, the deployment needs:

1. **Identity and authorization:** company SSO/MFA, role-based access, tenant-scoped authorization on every upload, job, report, and delete operation; short-lived secure sessions; audit logs that exclude payload contents.
2. **Network boundary:** TLS at the ingress, firewall/WAF or private gateway, inbound allow-listing, and outbound egress limited to the approved staging chatbot and secret/key-management services. The Python app itself is not a firewall.
3. **Data minimization:** synthetic or redacted benchmarks by default; explicit approved fields and retention; payloads and reports excluded from application, reverse-proxy, analytics, crash, and access logs. Prevent raw prompts/reports from being sent to third-party model providers unless the company has explicitly approved that data flow.
4. **Storage protection:** encryption in transit and at rest using company-managed KMS/HSM keys; separate per-tenant or per-job data-encryption keys; no plaintext temporary files or unencrypted swap; controlled snapshots/backups and documented retention.
5. **Deletion lifecycle:** stop/finish jobs; delete uploaded inputs, reports, indexes, temporary files, browser/session references, and replicas; expire backups under a documented schedule. For fast cryptographic erasure, use a unique per-job encryption key protected by KMS and destroy that key, then verify that no plaintext copies or alternate keys remain. Emit a signed/auditable deletion receipt with object IDs, key-destruction status, time, and backup-retention status.
6. **Verification and operations:** threat model, dependency/image scanning, independent penetration test, incident response, access reviews, retention drills, and tested restore/delete procedures. A dashboard success message alone is not evidence of secure erasure.

## What “secure erasure” can honestly mean

Deleting a file in Python (`unlink`/`rmtree`) is logical deletion from the application's visible filesystem. On cloud storage, snapshots, replicas, wear-leveling flash, provider logs, and backups may be outside the app's control. NIST media sanitization guidance treats sanitization as a controlled process intended to make recovery infeasible for a defined level of effort; cryptographic erase depends on encryption and complete control of the relevant keys and copies. It is not a universal mathematical guarantee.

Before any product claim, the hosting provider, storage/KMS design, backup lifecycle, and contractual deletion commitments must be verified. Until then, the product should say **“application data deletion requested/completed”**, with the scope and backup-retention caveat, rather than **“securely erased”** or **“guaranteed erased.”**

## Deployment decision

The current public Space remains synthetic-only. A first company API pilot is now supported through `python3 -m app.session_eval --target company-api`; it must run inside a company-approved private CI/network, use an approved secret injection, and keep output/report storage within that boundary. Its default report omits raw messages and answers. This pilot is not ready for production company data until the organization has implemented and verified its own identity, storage encryption, key-management, egress, audit, and backup controls. Do not enter a company's real credentials into the public demo.
