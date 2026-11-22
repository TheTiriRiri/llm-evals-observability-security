# Production AI Engineering — Workshop Labs

All labs are written in **Python 3.11+** and designed to run either against a live LLM API (`OPENAI_API_KEY`) or in **offline/mock mode** where noted so participants can iterate rapidly without hitting rate limits.

## Prerequisites & Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
cp .env.example .env
python -m spacy download en_core_web_sm   # Lab 5 (Presidio NER, ~12 MB)
python check_env.py                       # exits 1 if something required is missing
```

`OPENAI_API_KEY` is needed only for the live variants (real judge in Lab 1, `LIVE_EVAL=1` in Lab 3, the red-team scan in Lab 6; the Lab 6 regression tests run offline). The Lab 6 red team runs in local generation mode, so it needs no promptfoo account (details in the Lab 6 README). Langfuse keys are optional: without them Lab 2 prints the trace locally. Run `check_env.py` a few days before the workshop, not on the morning of.

**Facilitator: API keys and rate limits.** Give each participant their own key with a spend limit instead of one shared key: twenty laptops on one key hit HTTP 429 within minutes. Live calls run `LIVE_WORKERS` at a time (default 4), and the client retries 429s with backoff; lower `LIVE_WORKERS` if 429s persist. Every live step has an offline plan B: `--mock` in Lab 1, the recorded fixtures in Lab 3, the replay tests in Lab 6.

For **Lab 3** and **Lab 6**, install Promptfoo (Node.js 18+ required):
```bash
npm install -g promptfoo
```

For **Lab 6** (optional: a broad probe of the bare model, not of your guardrails):
```bash
pip install garak
```

## Lab Index

| Lab | Day | Topic | Directory |
| :--- | :--- | :--- | :--- |
| **Lab 1** | Day 1 | Failure Analysis & Calibrated LLM-as-a-Judge | [lab1_evals_and_judge/README.md](./lab1_evals_and_judge/README.md) |
| **Lab 2** | Day 1 | Tracing a Multi-Step Agent & Bottleneck Diagnosis | [lab2_observability/README.md](./lab2_observability/README.md) |
| **Lab 3** | Day 1 | CI/CD Regression Gate (`promptfoo` + `pytest`) | [lab3_ci_gate/README.md](./lab3_ci_gate/README.md) |
| **Lab 4** | Day 2 | Threat Modeling an Agentic RAG App | [lab4_threat_modeling/README.md](./lab4_threat_modeling/README.md) |
| **Lab 5** | Day 2 | Breaking & Hardening a Vulnerable Assistant | [lab5_attack_and_harden/README.md](./lab5_attack_and_harden/README.md) |
| **Lab 6** | Day 2 | Runtime Guardrails & Automated Red Teaming | [lab6_guardrails_and_redteam/README.md](./lab6_guardrails_and_redteam/README.md) |
