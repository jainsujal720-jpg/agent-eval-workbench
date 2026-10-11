# AgentEval deployment modes

AgentEval will have two deployment modes built from the same evaluation code. They have different trust boundaries and must not share customer data.

## Mode A — public Hugging Face demo

- Purpose: let visitors try the interface and understand benchmark evaluation.
- Data: synthetic or public benchmarks only.
- Chatbot: deterministic local fixtures; no company API and no paid model credential.
- Upload/report handling: browser-cookie scoping, best-effort credential detection, app-level clearing and idle cleanup. These are demo safeguards, not company authentication or secure-erasure guarantees.
- Status: demo deployment path. Do not enter real customer or company-confidential data.

See [`HUGGINGFACE_SPACE.md`](HUGGINGFACE_SPACE.md).

## Mode B — company-controlled evaluation

### First private pilot: AWS Fargate job inside the company boundary

The selected direction is a one-shot ECS Fargate task in the company's AWS account and private network. The company keeps its benchmark, staging endpoint, secret, and report destination under its controls. AgentEval sends test turns only to the approved **staging** API over HTTPS. The API token is injected at runtime as `AGENTEVAL_AUTH_TOKEN`; it is not put in benchmark JSON, source control, or the command line. The current adapter supports a configured token/header. The AWS task, IAM roles, Secrets Manager integration, and network policy have not been provisioned yet.

Example command inside the private task:

```bash
python3 -m app.session_eval \
  --target company-api \
  --benchmark benchmarks/company-sanitized.jsonl \
  --output /approved/private-path/agenteval-summary.json
```

Configure `AGENTEVAL_CHAT_URL` to the staging API over HTTPS and inject `AGENTEVAL_AUTH_TOKEN` from the approved secret manager. Configure request/response mappings using [`COMPANY_API_ADAPTER.md`](COMPANY_API_ADAPTER.md). The default company report is summary-only: it omits case IDs, user inputs, agent answers, and free-text failure details. Raw content is held in process memory while testing. `--include-content` opts into saving a full report and should be used only when the destination is approved encrypted storage with an explicit retention policy.

The current public GitHub repository is not a suitable place for private benchmark files or real company API secrets. A company should use its private source-control project/environment and run a workflow revision that security reviewers have approved. **Never attach a self-hosted runner with access to company networks or secrets to this public repository.** GitHub warns that untrusted pull-request code can compromise self-hosted runners, particularly for public repositories. See [GitHub's secure-use guidance](https://docs.github.com/en/actions/reference/security/secure-use).

The private pilot command is a first integration path, not a complete enterprise security product. It does not add SSO, tenant accounts, KMS lifecycle controls, firewall rules, backup sanitization, or a cryptographic-erasure receipt. The company must control network access, task roles, logs, output path, and retention. See [`AWS_PRIVATE_PILOT.md`](AWS_PRIVATE_PILOT.md) for the staged AWS design.

### Later private dashboard

Only after selecting a company hosting platform should we add the internal multi-user dashboard, SSO, per-tenant authorization, KMS-backed encrypted storage, and provider-specific deletion workflow. The dashboard should run inside the company's VPC/on-prem network, reachable only through its identity-aware gateway. We should not expose it publicly or send raw reports to public CI artifacts.

## Required release gates before sensitive-data pilot

1. Company security team approves the deployment and data classification.
2. Staging API is isolated from production actions; its credential is least-privilege and rotated.
3. Network policy restricts inbound users and outbound destinations.
4. CI logs and artifacts are checked to contain no raw prompts, answers, tokens, or identifiers.
5. Reports use company-approved storage and retention; raw content remains off by default.
6. Deletion and backup expiry are tested and documented against the chosen hosting provider.
7. Independent threat-model review and penetration testing are completed before a production claim.

## AWS pilot prerequisites

The company account owner must choose the approved AWS account and Region, identify the private VPC/subnets, and confirm how the staging API is privately reachable. Build and validate the first task using synthetic data only. The public Space stays synthetic-only regardless of that choice. See [`AWS_PRIVATE_PILOT.md`](AWS_PRIVATE_PILOT.md) for the implementation stages and review gates.
