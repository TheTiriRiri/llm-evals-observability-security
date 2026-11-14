# Lab 3: CI/CD Regression Gate (`promptfoo` + `pytest`) (30 min)

## Goal
1. Inspect `prompt_baseline.txt` vs. `prompt_candidate_regressed.txt`. Notice the candidate improves friendliness but **drops the citation requirement** (a silent regression!).
2. Run the `pytest` CI gate to verify that deterministic + faithfulness thresholds catch the regression.
3. Optionally run `promptfoo eval` for a side-by-side HTML matrix comparison.
4. Fix `prompt_candidate_regressed.txt` so all CI gates pass.

Both prompt files are complete templates with `{{context}}` and `{{query}}` placeholders. `pytest` and `promptfoo` fill them the same way and read the same `golden_dataset.jsonl` (promptfoo test-case format: `{"description": ..., "vars": {...}}`).

## Run

```bash
# Run pytest CI gate (offline simulation by default; set LIVE_EVAL=1 to call the real model)
pytest lab3_ci_gate/test_ci_gate.py -v
LIVE_EVAL=1 pytest lab3_ci_gate/test_ci_gate.py -v

# Optional: Promptfoo side-by-side comparison (requires OPENAI_API_KEY in ../.env)
cd lab3_ci_gate
promptfoo eval --env-file ../.env
promptfoo view
```

`promptfoo eval` exits with code 100 when any test fails. With the regressed candidate that is expected, so run `promptfoo view` as a separate command, not after `&&`. In CI the same non-zero exit code is what blocks the merge.

`test_candidate_passes_ci_gate` is expected to FAIL until you fix the candidate prompt.
