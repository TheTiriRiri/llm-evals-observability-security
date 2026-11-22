# Lab 3: CI/CD Regression Gate (`promptfoo` + `pytest`) (30 min)

A teammate opens a PR that "only makes the assistant friendlier". The JSON format and the citations are untouched. Your gate has to decide whether it can merge.

## Goal
1. **Read the PR (5 min).** Diff `prompt_baseline.txt` and `prompt_candidate_regressed.txt`. Besides the tone, what behaviour changed? Predict which rows of `golden_dataset.jsonl` will regress.
2. **Run the gate (5 min).** Schema validity is 100% and the overall pass rate clears the 90% bar, yet the gate fails. Read the per-slice table and the list of cases that flipped from PASS to FAIL.
3. **Discuss (5 min).** Why does the aggregate threshold let this through? What do the intervals on a 2-row slice tell you? How many rows would you want per critical slice?
4. **Fix the candidate (10 min).** Keep the friendlier tone, restore the abstention rule. Offline, an edited prompt has no recorded outputs, so the gate fails closed: evaluate your version with `LIVE_EVAL=1`, or compare with the reference fix (`PROMPT_CANDIDATE`, below).
5. **Optional (5 min).** Run the same dataset through `promptfoo` for a side-by-side HTML matrix, and the live faithfulness judge from Lab 1.

## Run

```bash
# Offline: replays the outputs recorded in fixtures/ for the shipped prompt versions
pytest lab3_ci_gate -v --tb=short

# Offline, reference fix instead of the regressed candidate
PROMPT_CANDIDATE=../solutions/lab3_prompt_candidate_fixed.txt pytest lab3_ci_gate -v --tb=short

# Live model; also runs the faithfulness judge from Lab 1 (your prompt, or the reference one)
LIVE_EVAL=1 pytest lab3_ci_gate -v --tb=short
LIVE_EVAL=1 JUDGE_PROMPT_FILE=solutions/lab1_judge_prompt.txt pytest lab3_ci_gate -v --tb=short

# Re-record the fixtures from the real model
LIVE_EVAL=1 RECORD_FIXTURES=1 pytest lab3_ci_gate

# Optional: promptfoo side-by-side comparison (requires OPENAI_API_KEY in ../.env)
cd lab3_ci_gate
promptfoo eval --env-file ../.env
promptfoo view
```

`test_candidate_no_slice_regression` is expected to fail until you fix the candidate. The live faithfulness test is skipped unless `LIVE_EVAL=1`. `test_gate_scoring.py` tests the gate's own scoring rules and always passes.

## How the gate works
- **Dataset.** `golden_dataset.jsonl` has 20 rows in promptfoo's test-case format: 18 `answerable` (the expected fact and citation must appear) and 2 `not_covered` (the context does not answer the question; the assistant must say so instead of guessing). `pytest` and `promptfoo` read the same file and render the prompts the same way. Each row carries a frozen `context`, so the gate tests the generator only: a change to retrieval (chunking, embeddings, top-k) needs an eval with retrieval in the loop.
- **Rules.** Schema validity 100%; overall pass rate ≥ 90%; and, as a paired comparison on the same inputs, no slice may drop more than 5 points below the baseline. Deterministic checks run everywhere; semantic faithfulness needs a live judge and is computed over the answers with a valid schema. A `not_covered` row passes only with an abstention phrase and an empty `citations` list. The phrase check is a short regex shared with Lab 1, so a new paraphrase ("does not contain", "couldn't find") shows up as a false failure: read the flipped cases before you widen it.
- **Fixtures.** Offline, the gate replays `fixtures/<prompt>.json`, keyed by the SHA-256 of the prompt file. The shipped fixtures are hand-written examples of how a model typically answers each prompt, so the lab runs without an API key; they are not recordings. `RECORD_FIXTURES=1` replaces them with real outputs. A prompt without a matching fixture fails: a gate must never pass a prompt nobody evaluated.
- **Small slices.** 0/2 vs 2/2 is enough to block the merge, but a 2-row slice has a 95% interval of 34–100% even when everything passes. In a real gate, give each critical slice (abstention, safety, high-value intents) enough rows to mean something, and run the full set nightly.
- **promptfoo's grader** (`llm-rubric`) is an uncalibrated LLM judge. Read its failures as leads; the judge you calibrated in Lab 1 is the one the pytest gate uses.
- `promptfoo eval` exits with code 100 when any test fails. With the regressed candidate that is expected, so run `promptfoo view` as a separate command, not after `&&`. In CI the same non-zero exit code is what blocks the merge.
