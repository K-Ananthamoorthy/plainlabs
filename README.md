# PlainLabs

Private, agentic lab-report explainer that runs on a small on-device model.
Upload a lab report, get a plain-language explanation with safety guardrails.
See [docs/PRD.md](docs/PRD.md). Day-1 build in progress.

```bash
uv sync
ollama pull gemma4:e2b-it-qat
uv run python -m plainlabs evals/golden/report_basic.txt
```
