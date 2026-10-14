# Personal AWS synthetic tool-failure stress test

## Scope

This is a disposable learning exercise in a personal AWS account. It runs only the repository's local synthetic tool-failure benchmark: 16 conversations and 20 turns, including timeouts, outages, malformed and inconsistent tool responses, and recovery after a retry. It does not call OpenAI, a company chatbot, or any customer system, and it does not use a secret.

The task runs in one existing default subnet in `ap-south-1`. It receives a public IPv4 address so Fargate can pull the image and send logs, but its dedicated security group has **no inbound rules**. Outbound access is limited to HTTPS and VPC DNS. This is not the private-network company pilot and must never be used with real company or customer data.

## Observed AWS run

The AWS run result reported during this project showed the **session benchmark** profile: 8 conversations and 18 turns. Its summary was `provider: demo`, `passed: true`, with 0 failed turns, 0 access-check failures, 0 errors, 0 handled tool failures, and 4 guard interventions. The Fargate task exited with code 0. All inputs and fixtures were synthetic; this run did not call OpenAI, a company chatbot, or a customer system.

Keep that result separate from the harder tool-failure benchmark described by this guide. The session benchmark has 8 conversations / 18 turns (`benchmarks/support_sessions.jsonl`); the tool-failure benchmark has 16 conversations / 20 turns (`benchmarks/support_failures.jsonl`). A passing result for one suite does not mean the other suite ran or passed. When repeating a run, verify the task definition's `Command` names the intended benchmark before launching the task, then record the report's case counts with its metrics.

## Resources created by the stack

- Private ECR repository with image scanning, AES-256 encryption, one-image lifecycle, and force-empty deletion.
- One ECS cluster and one Fargate task definition (ARM64, 0.25 vCPU, 512 MiB).
- A task execution role scoped to pull this repository's image and write to this log group.
- A task role with no attached permissions.
- One security group with no inbound access.
- One CloudWatch log group with three-day retention.

There is no always-running service, load balancer, NAT gateway, customer API credential, or public dashboard. AWS charges may still apply for Fargate task runtime, the temporary public IPv4 address, ECR image storage, and log ingestion/storage. Delete the stack after the test. Check the AWS Pricing page for current Region pricing before deployment.

## Prerequisites

- AWS CLI v2 signed in to the account.
- Docker Desktop running.
- The project files, including `Dockerfile`, `app/`, and `benchmarks/support_failures.jsonl`.
- Confirmed VPC and subnet values in the target Region. Never commit account-specific IDs to the public repository.

## 1. Validate the template without creating resources

From the project root:

```bash
aws cloudformation validate-template \
  --template-body file://infra/aws/synthetic-smoke.yaml \
  --region ap-south-1
```

This validates the CloudFormation template. It does not create the stack.

## 2. Create the small resource stack

Use the VPC ID and CIDR confirmed in your account. This example uses the values from the current local setup; do not copy them into source code or Git:

```bash
aws cloudformation deploy \
  --template-file infra/aws/synthetic-smoke.yaml \
  --stack-name agenteval-synthetic-smoke \
  --region ap-south-1 \
  --capabilities CAPABILITY_IAM \
  --parameter-overrides VpcId=YOUR_VPC_ID VpcCidr=172.31.0.0/16
```

Replace `YOUR_VPC_ID` with the VPC ID from the read-only check. The VPC ID is an account-specific value; keep it in your local Terminal command rather than committing it to the public repository.

The stack creates billable AWS resources. Review the command and the resource list above before running it. To inspect its outputs:

```bash
aws cloudformation describe-stacks \
  --stack-name agenteval-synthetic-smoke \
  --region ap-south-1 \
  --query 'Stacks[0].Outputs' \
  --output table
```

Copy the `RepositoryUri`, `ClusterName`, `TaskDefinitionArn`, `SecurityGroupId`, and `LogGroupName` outputs for the following steps.

## 3. Build and push the synthetic image

Run these from the project root. For `docker login`, replace `YOUR_AWS_ACCOUNT_ID` with the account ID shown in the `RepositoryUri` output. For `docker tag` and `docker push`, replace `YOUR_REPOSITORY_URI` with that full repository URI. The ARM64 build matches the Mac and Fargate task architecture.

```bash
aws ecr get-login-password --region ap-south-1 | docker login --username AWS --password-stdin YOUR_AWS_ACCOUNT_ID.dkr.ecr.ap-south-1.amazonaws.com
docker buildx build --platform linux/arm64 --load -t agenteval-synthetic-smoke:smoke .
docker tag agenteval-synthetic-smoke:smoke YOUR_REPOSITORY_URI:smoke
docker push YOUR_REPOSITORY_URI:smoke
```

Replace the placeholders with values from the stack output. Do not add credentials to these commands; ECR login uses the AWS CLI's temporary session.

## 4. Run the one-shot task

Use one of the default subnet IDs shown for `ap-south-1`, the security group output, and the task definition ARN output:

```bash
aws ecs run-task \
  --cluster agenteval-synthetic-smoke \
  --task-definition YOUR_TASK_DEFINITION_ARN \
  --launch-type FARGATE \
  --platform-version LATEST \
  --network-configuration 'awsvpcConfiguration={subnets=[YOUR_DEFAULT_SUBNET_ID],securityGroups=[YOUR_SECURITY_GROUP_ID],assignPublicIp=ENABLED}' \
  --region ap-south-1
```

The task has no port mapping and the security group has no inbound rules, so it does not serve an internet-accessible app. It runs the local demo evaluator and exits. Save the returned task ARN.

Wait for completion:

```bash
aws ecs wait tasks-stopped \
  --cluster agenteval-synthetic-smoke \
  --tasks YOUR_TASK_ARN \
  --region ap-south-1
```

Check the exit code (zero means the evaluation command completed successfully):

```bash
aws ecs describe-tasks \
  --cluster agenteval-synthetic-smoke \
  --tasks YOUR_TASK_ARN \
  --region ap-south-1 \
  --query 'tasks[0].{LastStatus:lastStatus,StoppedReason:stoppedReason,ExitCode:containers[0].exitCode,LogStream:containers[0].logStreamName}' \
  --output table
```

Open the `LogStream` in CloudWatch Logs under `/agenteval/synthetic-smoke` to inspect the summary metrics. The task uses `--summary-only`, so it logs metrics and numbered check outcomes without prompts or answers. A passing local demo run of this suite reports 16 sessions, 20 turns, zero failed turns, and 9 handled tool failures. The AWS run is synthetic; it is not evidence about a real chatbot.

## 5. Read AWS results in the local dashboard

The AWS run does not automatically appear in the dashboard. While the stack and CloudWatch log group still exist, sync the summary into a local report:

```bash
python3 -m app.aws_runs --region ap-south-1
```

This command reads the task log streams through the AWS CLI and saves only pass/fail, aggregate metrics, and numbered check outcomes to `reports/aws-runs.json`. It does not copy customer prompts, answers, credentials, or raw logs. The file stays on your Mac and is ignored by Git. When you sync another run after recreating the stack, it keeps earlier summaries in the same local file.

Start the local dashboard on an available port:

```bash
python3 -m app.dashboard --port 8001
```

Open [http://127.0.0.1:8001/aws-runs](http://127.0.0.1:8001/aws-runs). If port 8001 is already in use, choose another port such as 8002 and use that number in the URL. The dashboard reads the saved local report; opening it does not call AWS.

If the stack was already deleted, its CloudWatch log group is gone and cannot be synced. The local dashboard copy remains available. New runs are merged into the local report so the prior summary is retained.

## 6. Delete the stack after saving results

First sync any result you want to keep (step 5). Then remove the cluster, task definition, roles, security group, log group, ECR repository, and its image:

```bash
aws cloudformation delete-stack \
  --stack-name agenteval-synthetic-smoke \
  --region ap-south-1
```

Wait for deletion to finish before rebuilding the stack with the harder benchmark:

```bash
aws cloudformation wait stack-delete-complete \
  --stack-name agenteval-synthetic-smoke \
  --region ap-south-1
```

The local `reports/aws-runs.json` copy and local Docker image are not deleted with the stack. This removes the AWS resources created by the stack; it is not a company-data erasure guarantee.

## Next boundary

This quick test intentionally uses a public subnet and a public IP for outbound service access. The later company pilot must use a company-approved account, a private subnet with no public IP, approved egress, least-privilege identity, and company-approved data/log retention. Do not convert this synthetic stack into a real-data deployment by changing only its benchmark file.
