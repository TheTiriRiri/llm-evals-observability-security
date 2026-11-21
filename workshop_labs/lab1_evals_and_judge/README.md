# Lab 1: Failure Analysis & Calibrated LLM-as-a-Judge (35 min)

## Data
`traces_sample.jsonl` holds 40 traces from a RAG support bot: 20 `dev`, 20 `val`. Each trace has the query, the retrieved documents (tagged `[ID]`), the raw model output, and one human label per failure mode:

| Field | Meaning |
| :--- | :--- |
| `labels.format` | Valid JSON with `answer` and `citations` |
| `labels.citation` | Citations present (unless the answer says the docs do not cover the question) and every cited ID is in the retrieved context |
| `labels.faithfulness` | Every claim is supported by the retrieved context; a "the docs do not cover this" answer counts as faithful |
| `human_label` | Overall verdict: FAIL if any of the above fails |

`null` means "not applicable": an output that is not JSON gets no citation or faithfulness label.

## Goal
1. **Failure analysis (10 min).** Read the 20 `dev` traces without looking at `labels` or `failure_note`. Write a short note on every bad trace (open coding), group the notes into failure modes (axial coding) and rank them by frequency × severity. Only then compare with `failure_note`.
2. **Deterministic checks (3 min).** `check_format` and `check_citations` are already implemented. Read them: which of your failure modes do they catch, and which can only a semantic evaluator catch?
3. **Baseline judge (5 min).** Run the vague 1–5 rubric (`--judge likert`) and read its disagreements. Look for two patterns: correct "the documentation does not cover this" answers marked as bad, and fluent, confident inventions marked as good.
4. **Binary judge (12 min).** Rewrite `JUDGE_SYSTEM_PROMPT` (binary PASS/FAIL, reasoning before the verdict) around the failure modes from step 1. Iterate on `dev` only.
5. **Held-out estimate (5 min).** Freeze the prompt and run `--split val` once. Report the judge's precision and recall with their intervals; the target is ≥ 0.85 for both as point estimates.

## Run

```bash
# Offline: deterministic checks + a crude numeric stand-in for the judge (no API cost)
python lab1_evals_and_judge/judge_starter.py --mock

# Live (OPENAI_API_KEY from .env): the 1-5 baseline, then your binary judge, both on dev
python lab1_evals_and_judge/judge_starter.py --judge likert
python lab1_evals_and_judge/judge_starter.py

# Final report on the held-out split, once your prompt is frozen
python lab1_evals_and_judge/judge_starter.py --split val

# Reference prompt, for comparison after you have written your own
python lab1_evals_and_judge/judge_starter.py --judge-prompt solutions/lab1_judge_prompt.txt
```

## How to read the report
- Each evaluator is scored only against the label of its own failure mode. Scored against `human_label`, a faithfulness judge would get credit for JSON and citation errors it never checks: `t07` is a faithful answer that fails only on its missing citation.
- The positive class is FAIL, i.e. a caught failure. Precision: how often a FAIL from the evaluator is a real failure. Recall: how many real failures it catches. Kappa: agreement corrected for chance.
- `val` has 8 faithfulness failures. One miss moves recall by 12.5 points, and the 95% interval spans tens of points. Read the disagreements, not just the scores. A judge you trust in CI needs a few hundred labels, and the human labelers should first agree with each other (inter-annotator kappa) before you compare the judge with them.
- Do not tune the judge prompt on `val`, or its estimate stops being honest.
- `--mock` replaces the judge with a heuristic that flags numbers missing from the context. It misses non-numeric failures on purpose, so mock scores are not a target.
