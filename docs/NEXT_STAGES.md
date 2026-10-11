# AgentEval priorities and Hugging Face reminder

## Current implementation stage

- [x] Update GitHub Actions to Node 24 compatible action releases and pin Ubuntu 24.04.
- [x] Expand CI across unit, single-request release, session authorization, and tool-failure suites; upload the stress benchmark as a known baseline report.
- [x] Add negative regression cases proving fabricated order status, unsafe refund approval, and wrong routes fail evaluation.
- [x] Queue dashboard runs in a background worker, show turn progress, retain unique reports, and provide run history.
- [x] Configure company API URL, HTTPS enforcement, request field names, bearer/custom-header auth, response JSON paths, health metadata, and request timeout.
- [x] Run the expanded suite locally and merge the tested hardening PR to `main`.

## Hugging Face demo in progress

- [x] Add a Docker Space entry point, port configuration, sample benchmark download, and a deterministic synthetic-only runtime.
- [x] Isolate public-demo uploads, jobs, and reports by browser session; add clear-data and 30-minute idle cleanup.
- [ ] Build and run the Docker image locally, then review the public-data warning and sample benchmark flow.
- [ ] Create a Hugging Face Docker Space and push the Space files to its repository.
- [ ] Confirm the Space build completes and test upload, run, report, and restart behavior.

## Company-controlled evaluation path

- [x] Add a CLI target for an approved HTTPS company staging API.
- [x] Require a runtime-injected API token for that target and keep raw case details out of stdout.
- [x] Save a summary-only company report by default; require an explicit `--include-content` flag to save raw prompts and answers.
- [ ] Run this only from the selected AWS private pilot: a one-shot ECS Fargate task in the company account/VPC, with the staging secret supplied by Secrets Manager.
- [ ] Confirm the company-approved AWS account, Region, private subnets, staging endpoint reachability, and report destination. Do not put credentials in chat or Git.
- [ ] Implement and review the private ECR image, least-privilege ECS roles, task definition, egress restrictions, summary-only logging, and deletion/retention evidence using synthetic data first.
- [ ] Add an internal dashboard only after SSO and tenant-scoped access control are designed and reviewed.

See [`AWS_PRIVATE_PILOT.md`](AWS_PRIVATE_PILOT.md). AWS resources have not been provisioned.

## Later deployment milestone (keep on roadmap)

Keep the public Docker Space synthetic-only. The company test path runs separately inside a customer-controlled private CI/network. Before any company data is used, complete the environment-specific security, storage, retention, and deletion controls in [`SECURITY_AND_ERASURE.md`](SECURITY_AND_ERASURE.md) and [`DEPLOYMENT_MODES.md`](DEPLOYMENT_MODES.md). No model weights are uploaded because this project calls a hosted OpenAI model and does not own model weights.
