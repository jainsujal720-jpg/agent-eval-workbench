# AgentEval priorities and Hugging Face reminder

## Current implementation stage

- [x] Update GitHub Actions to Node 24 compatible action releases and pin Ubuntu 24.04.
- [x] Expand CI across unit, single-request release, session authorization, and tool-failure suites; upload the stress benchmark as a known baseline report.
- [x] Add negative regression cases proving fabricated order status, unsafe refund approval, and wrong routes fail evaluation.
- [x] Queue dashboard runs in a background worker, show turn progress, retain unique reports, and provide run history.
- [x] Configure company API URL, HTTPS enforcement, request field names, bearer/custom-header auth, response JSON paths, health metadata, and request timeout.
- [ ] Run the updated suite in local Mac/GitHub Actions and merge the tested PR.

## Later deployment milestone (keep on roadmap)

After the four priorities above are verified and merged, adapt this app to a Docker-based Hugging Face Space and host the interactive demo. Before publication, use only synthetic fixtures and sample benchmarks, configure any model key as a Space secret, expose the app on the Space-required port, and clearly label that the demo is not a production company integration. Optionally publish a separately documented synthetic benchmark dataset. No model weights are uploaded because this project calls a hosted OpenAI model and does not own model weights.
