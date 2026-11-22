# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repository is

Materials for a 2 × 3.5 h workshop, "Production AI Engineering: Evals, Observability & Security". The root holds the prose: `curriculum.md`, `slides_and_facilitator_notes.md` and `appendix_take_home.md`. `workshop_labs/` holds six Python labs plus reference solutions in `solutions/`. Participants run the code, and every lab works offline by default.

## Commands

Run all Python from `workshop_labs/`. Imports such as `lab1_evals_and_judge.*` and `solutions.*` resolve from there, and `pyproject.toml` sets `pythonpath = ["."]` for pytest.

```bash
# Setup
python3 -m venv .venv && source .venv/bin/activate
pip install -e .
python -m spacy download en_core_web_sm   # Lab 5 (Presidio NER)
python check_env.py                       # exits 1 if something required is missing
npm install -g promptfoo                  # Labs 3 and 6 only

# Tests (offline, no API key)
pytest                                                        # testpaths: every lab with code (labs 1, 2, 3, 5, 6)
pytest solutions/lab6_test_redteam_regressions_solution.py -v
pytest solutions/lab5_test_hardened_app_solution.py -v       # needs Presidio + en_core_web_sm
pytest lab6_guardrails_and_redteam/test_redteam_regressions.py::test_replay_kb_injection_without_approval_sends_nothing -v
PROMPT_CANDIDATE=../solutions/lab3_prompt_candidate_fixed.txt pytest lab3_ci_gate   # gate against the reference fix

# Labs (offline)
python lab1_evals_and_judge/judge_starter.py --mock            # also: --split val, --judge likert, --judge-prompt solutions/lab1_judge_prompt.txt, --show t07
python lab2_observability/slow_rag_agent.py --requests 10
python -m solutions.lab2_fast_rag_agent --requests 10
python lab5_attack_and_harden/vulnerable_app.py
python -m solutions.lab5_hardened_app
```

Two results are expected, not bugs:
- `lab3_ci_gate::test_candidate_no_slice_regression` fails by design. The shipped candidate prompt regresses the `not_covered` slice, and catching that is the point of the lab.
- `test_candidate_faithfulness_live` is skipped unless `LIVE_EVAL=1`.

Each lab with code also has tests of its own plumbing, green from the start and independent of the participants' TODOs: `lab1_evals_and_judge/test_judge_runner.py`, `lab2_observability/test_tracing.py`, `lab3_ci_gate/test_gate_scoring.py`, `lab5_attack_and_harden/test_rehydrate.py`, `lab6_guardrails_and_redteam/test_agent_runtime.py`. They replace the OpenAI client and Langfuse with stand-ins, so they never call a live service.

No linter or formatter is configured.

Live runs and switches:
- **`.env`** comes from `.env.example`. It holds `OPENAI_API_KEY` and `OPENAI_MODEL` (default `gpt-4o-mini`; keep the model configurable), plus optional `LANGFUSE_*` keys for Lab 2.
- **Live calls in Labs 1 and 3** share `openai_client()` (`max_retries=5`) and `parallel_map()` from `judge_starter.py`. `LIVE_WORKERS` (default 4) sets how many run at once.
- **Lab 3:**
  - `LIVE_EVAL=1` calls the real model.
  - `RECORD_FIXTURES=1` re-records the fixtures.
  - `PROMPT_CANDIDATE` is a path relative to `lab3_ci_gate/`.
  - `JUDGE_PROMPT_FILE` selects the judge prompt.
- **Lab 6:**
  - `GUARDRAILS_IMPL=solution` swaps in the solution guardrails.
  - `REDTEAM_HITL_APPROVED=1` simulates approval fatigue.
  - The promptfoo scan runs from inside `lab6_guardrails_and_redteam/` with `PROMPTFOO_DISABLE_REDTEAM_REMOTE_GENERATION=true`. The exact commands are in that lab's README.

## Architecture

**Starters and solutions are layered.**
- Each solution imports names and data from its starter:
  - `solutions/lab2_fast_rag_agent.py` from `lab2_observability/slow_rag_agent.py`
  - `solutions/lab5_hardened_app.py` from `lab5_attack_and_harden/vulnerable_app.py`
  - `solutions/lab6_guardrails_solution.py` from `lab6_guardrails_and_redteam/guardrails.py`
- Renaming or changing data in a starter can break its solution, so run both after any starter edit.
- Lab 3 imports its abstention regex, document-ID pattern, judge, `wilson_interval`, `openai_client` and `parallel_map` from `lab1_evals_and_judge/judge_starter.py`. Changes there change the Lab 3 gate.

**Nothing needs an API key by default.**
- Lab 1 has a `--mock` judge.
- Labs 2 and 5 simulate latencies and the model. Lab 5's simulated model follows injections on purpose.
- Lab 3 replays fixtures.
- Lab 6 replays scripted model turns.
- Lab 4 is a paper exercise: `architecture.md`, the worksheet and `solutions/lab4_threat_model_solution.md`.

**Lab 3 gate.**
- `golden_dataset.jsonl` uses promptfoo's test-case format. Both `test_ci_gate.py` and `promptfooconfig.yaml` read it and render the prompts the same way.
- Offline, the gate replays `fixtures/<prompt stem>.json`. Each fixture has the keys `prompt_file`, `prompt_sha256`, `source` and `outputs`, and is keyed by the SHA-256 of the prompt file.
- Any edit to a prompt file orphans its fixture, and the gate then fails closed. To fix that:
  - re-record with `LIVE_EVAL=1 RECORD_FIXTURES=1`, or
  - update the fixture's hash and outputs by hand.
- The shipped fixtures are hand-written, not recordings.
- A `not_covered` row passes only with an abstention phrase **and** an empty `citations` list. The JavaScript assertion in `promptfooconfig.yaml` mirrors `score_row()`; change both together.
- `check_faithfulness()` divides by the answers with a valid schema, never by all rows.

**Lab 5 re-hydration.**
- `rehydrate()` in `vulnerable_app.py` is part of the fixed request flow. It runs a single pass, and a placeholder inside a URL becomes `REDACTED`, even on an allowlisted host.
- `neutralize_placeholders()` defuses placeholder-shaped text planted in documents before redaction. `presidio_engines()` builds the Presidio engines once, pinned to `en_core_web_sm`.

**Lab 6 system under test.**
- `redteam_target.py` is one agent loop with two entry points:
  - promptfoo calls `call_api()`, which reads the session from `options["config"]["session"]`.
  - Tests call `run_agent(prompt, principal, client=ScriptedClient(...), guards=..., hitl_approved=...)`, using the scripted replies from `replay.py`.
- Every tool call is first parsed against its Pydantic argument model (`TOOL_ARGS`, `extra="forbid"`, `strict=True`; `TOOLS` is generated from them). Unknown fields and wrong types fail closed with a `tool_args` event.
- Then it passes `check_tool_policy(tool, args, principal, hitl_approved)` in this order: unknown tool → role → object-level authorization → recipient allowlist → HITL last.
- The runtime keeps its own `run.tool_log`. The output guardrail checks only the model's reply. `call_api()` returns `transcript(run)`: the reply, then the tool log under `TOOL_LOG_HEADER`, with reply lines that imitate the log removed. The `graderExamples` in `promptfooconfig_redteam.yaml` use that format, and a test checks it.
- Identity comes from the server-side `SESSIONS`, never from the model or the request.
- Help-center articles (`KB_ARTICLES`) are untrusted input. KB-0031 carries an obvious injection that the input tripwire quarantines. KB-0042 is a subtle one that only the tool policy stops.
- The guard module is injected (`guards=` in tests, `GUARDRAILS_IMPL` for promptfoo), so the same replays run against the starter and the solution.
- **Invariant:** the finding tests in `solutions/lab6_test_redteam_regressions_solution.py` must fail against the starter `guardrails.py` and pass against the solution.
- `SYSTEM_PROMPT` must appear line for line in the `prompt-extraction` plugin's `systemPrompt` in `promptfooconfig_redteam.yaml`. `test_scan_config_uses_the_real_system_prompt` enforces this.
- **Known limit, documented on purpose:** with `REDTEAM_HITL_APPROVED=1`, an injected `rotate_all_keys` from an admin session still runs. The curriculum uses it for the Rule of Two discussion, and the appendix turns it into a home exercise. Do not "fix" it silently.

## Documentation conventions

- **EN/PL twins.** The curriculum, slides, appendix, `workshop_labs/README.md` and every lab README have a Polish twin with the `-pl.md` suffix.
  - Each twin has the same line count and the same line-by-line structure: headings, list levels, tables, code blocks, links and URLs.
  - Edit both files in the same change.
  - Worksheets, payloads, `architecture.md` and solutions are English only.
- **Dated facts.** Facts that change over time are stated "as of November 2026", with sources, in `curriculum.md` and the appendix. This covers tool ownership, the OWASP LLM and Agentic Top 10 editions, the MCP spec revision, AI Act dates and GDPR changes.
  - Anything not confirmed by a primary source is marked **(to verify)** / **(do weryfikacji)**.
  - Re-check the source before changing such a fact.
- **Timing.** The agenda must fit two 210-minute days. When a unit or lab duration changes, update the schedule table in the curriculum and the slide timings so the totals still add up.

## Git

Commit messages are a single sentence on one line, with no AI markers: no "Claude" and no `Co-Authored-By` trailer.
