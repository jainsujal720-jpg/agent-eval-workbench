# Hugging Face Space demo

This Docker Space runs the AgentEval dashboard and its synthetic support chatbot in one container. The chatbot is pinned to the deterministic `demo` provider. It uses only the Alice/Bob fixture data in this repository, makes no OpenAI requests, and does not connect to any company system. **Do not add `OPENAI_API_KEY` to this public demo.** Anyone can submit a benchmark and start an evaluation; a public model key would let visitors spend your API budget.

## What a visitor can do

1. Open the Space and download the synthetic sample benchmark, or upload a JSON/JSONL conversation benchmark.
2. Review the test cases and expected routes before running them.
3. Run the deterministic demo and inspect conversation results and run history.

Uploads are limited to 256 KB, 50 conversations, and 100 turns; only one run can execute at a time. Each browser receives a random, HttpOnly session cookie. Uploads, job status, report history, and report downloads are scoped to that browser session, so another visitor cannot retrieve them by guessing a report link. The page has a **Clear my data** button. An inactivity cleanup removes the visitor's uploads and reports after 30 minutes; it waits for an active evaluation to finish. Hugging Face Spaces can also restart containers, and this demo does not attach persistent storage.

The browser's Back button or closing a tab is not a reliable signal to a server that data should be deleted. This demo uses the explicit clear button and server-side inactivity expiration instead. Even with isolation, use only synthetic or public test data because the Space is public and the project is a demo, not a security-certified data processor.

## Create the Space

1. On Hugging Face, create a new **Docker** Space. Choose **Public** only if you are comfortable with anyone using the demo and seeing the reports produced there. CPU Basic is sufficient; no GPU is needed.
2. Clone the new Space repository into a separate folder. Do not push your GitHub repository history as a direct replacement for the Space's initial history.
3. Copy `Dockerfile`, `.dockerignore`, and `README.md` from this project into the Space clone. Copy the `app/` directory and `benchmarks/support_sessions.jsonl` as well.
4. Commit and push those files to the Space's `main` branch. Hugging Face builds the Docker image and starts the app on port `7860`.
5. Wait for the Space build to finish, then open its URL. The root page redirects to the benchmark upload page.

No Hugging Face secret is required for the synthetic demo. If you later add a model-backed mode, make the Space private or add authentication, per-user quotas, request limits, and provider spending controls before setting a secret. Never expose an unrestricted paid model key through a public form.

## Local container check

From the project root, with Docker installed:

```bash
docker build -t agenteval-space .
docker run --rm -p 7860:7860 agenteval-space
```

Open `http://127.0.0.1:7860`. Stop the container with Control-C. The Space's app port and secret behavior follow Hugging Face's Docker Spaces documentation; app data written to the container filesystem is not persistent across restarts.
