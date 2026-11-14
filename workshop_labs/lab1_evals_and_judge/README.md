# Lab 1: Failure Analysis & Calibrated LLM-as-a-Judge (35 min)

## Goal
1. Perform **open & axial coding** on the first 20 traces in `traces_sample.jsonl` (`split == "dev"`) to identify the top 3 failure modes.
2. Implement a **deterministic code check** for structural/constraint failures (e.g., invalid JSON or missing required citation format).
3. Implement a **binary LLM-as-a-Judge** (`PASS` / `FAIL`) for **Groundedness / Faithfulness** that outputs reasoning *before* the verdict.
4. Calibrate your judge against `human_label` on the remaining 20 traces (`split == "val"`), aiming for **Precision >= 0.85** and **Recall >= 0.85**.

## Run

```bash
# Offline/mock mode (tests your deterministic checks & pipeline without API cost)
python lab1_evals_and_judge/judge_starter.py --mock

# Live mode (uses OPENAI_API_KEY from .env); iterate on the judge prompt against dev
python lab1_evals_and_judge/judge_starter.py --split dev

# Final report on the held-out split, once your prompt is frozen
python lab1_evals_and_judge/judge_starter.py --split val
```

`--split` defaults to `dev`. Do not tune the judge prompt on `val`, or your precision/recall stops being an honest estimate.

The `--mock` judge is a crude stand-in that only flags numbers missing from the context. It misses non-numeric contradictions on purpose, so mock-mode precision/recall is not a target to hit.
