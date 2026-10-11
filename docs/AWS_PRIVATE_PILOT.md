# AWS private pilot — planned deployment

## Goal

Run the AgentEval company-API CLI inside an AWS account and VPC controlled by the company. The first pilot is a one-shot job, not an internet-facing dashboard. The public Hugging Face Space remains a separate synthetic demo.

This document is an architecture and setup plan. It does **not** provision AWS resources and is not a production security certification.

## Pilot architecture

```text
Company-approved trigger
        │
        ▼
ECS Fargate task in private subnet ──HTTPS──► Company staging chatbot
        │
        ├── secret injected from AWS Secrets Manager
        └── summary-only result to approved private log/report destination
```

- **Compute:** ECS task on AWS Fargate, run to completion. No ALB or public dashboard in this pilot.
- **Network:** task uses private subnets and has no public IP. The task can reach only the approved staging API and the AWS services needed to pull its image, retrieve its secret, and emit the approved result. The exact route and egress policy must be set by the account owner.
- **Credential:** the staging API credential is stored in AWS Secrets Manager. ECS passes it into the task at runtime; it is not in the benchmark, Git, container image, or terminal command. Use a short-lived/read-only staging credential where the company API supports it.
- **Image:** store the reviewed AgentEval image in a private ECR repository and deploy a pinned image digest, not a mutable `latest` tag.
- **Input:** start with synthetic or anonymized benchmark cases. Do not bake confidential data into the Docker image or Git history. Before using real customer transcripts, the company must approve the source, transfer, retention, and deletion process.
- **Output:** use the CLI's default summary-only report. Do not enable `--include-content` unless the destination is approved encrypted storage and the retention policy is explicit. Do not write raw prompts or answers to CloudWatch logs.
- **Identity:** separate the ECS task execution role (image pull, log delivery, and the named secret retrieval) from the task role (no broad AWS permissions unless a reviewed design requires them). Scope IAM policies to exact resource ARNs.

AWS ECS supports Fargate tasks with `awsvpc` networking and task roles. ECS task definitions can inject a Secrets Manager secret into a container using the `secrets` field; AWS advises against plaintext environment entries for sensitive credentials. These mechanisms reduce exposure, but the running process still receives the token in memory/environment. [AWS ECS task definition documentation](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/task_definition_parameters.html)

Fargate task ephemeral storage is encrypted at rest by default on supported current platform versions, with AWS-owned or customer-managed key options. That is an at-rest protection; it does not by itself prove that all copies, logs, backups, or memory have been erased. [AWS Fargate ephemeral storage documentation](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/fargate-task-storage.html)

## Stages

### Stage 1 — confirm the AWS boundary

The company account owner chooses the account and AWS Region based on the company's data-residency rules, identifies the private VPC/subnets, and confirms where the staging chatbot is reachable. Do not use a personal AWS account for company data without written company approval. AWS usage can incur charges.

### Stage 2 — create least-privilege AWS identities

Create separate task-execution and task roles. Store the staging token in Secrets Manager. Limit retrieval to the specific secret ARN; do not grant `secretsmanager:*` or broad administrator access. Enable CloudTrail for administrative and secret-access events, while ensuring application logs do not include payloads or token values.

### Stage 3 — connect privately to staging

Use the staging API's HTTPS endpoint and validate its certificate. Security groups and route/firewall policy must allow only required outbound destinations. If the staging endpoint is outside the VPC, the company network team must choose and monitor a controlled egress path. The Python adapter's HTTPS check is not a firewall or egress allow-list.

### Stage 4 — run a synthetic smoke test

Build and scan the image, push it to private ECR, register a Fargate task definition, and run the existing synthetic benchmark. Check the result summary and verify CloudWatch output has metrics only. Do not attach real credentials/data until the company approves the review gates below.

### Stage 5 — approve real-data handling separately

If the company needs actual conversation data, define its approved source and minimization/redaction rules. Keep raw input and full reports inside company-controlled encrypted storage, with access controls, short retention, backups documented, and no model-provider transmission unless explicitly approved. Use the report's summary-only mode unless reviewers approve full-content output.

### Stage 6 — test deletion as an operational process

Test deletion of the benchmark object, report, temporary task files, logs, and any retained versions/replicas. Define backup expiry and prove which systems enforce it. Record a deletion receipt with scope, object/key identifiers, timestamp, and any backup-retention deadline. Describe this accurately as app/object deletion or cryptographic erasure for its documented scope; do not claim a universal guarantee.

## Review gates before any sensitive-data run

- Company security/privacy approval and data classification are recorded.
- Staging endpoint is separate from production and has no real transaction capability.
- Secret is stored in Secrets Manager and least privilege is verified.
- Fargate task has no public IP; network egress is reviewed and tested.
- Public GitHub and public Hugging Face do not receive the benchmark, secret, or raw report.
- CI/task logs and artifacts are checked for prompts, answers, tokens, and identifiers.
- Data retention, snapshots, backups, and deletion owner are documented.
- Threat model and independent security review are complete before any production claim.

## Not implemented yet

This repository currently has the CLI API target and summary-only report path. It does not yet contain AWS Terraform/CloudFormation, an ECS task definition, automated Secrets Manager retrieval wiring, SSO, a private dashboard, customer-managed per-run encryption keys, or a deletion receipt. Those require the actual account/VPC, region, secret ARN, approved staging endpoint, and company policies. We should build and validate that infrastructure against a non-production AWS account before handling sensitive company data.
