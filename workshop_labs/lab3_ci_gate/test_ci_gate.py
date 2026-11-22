"""Lab 3 CI regression gate: the candidate prompt must not regress any slice of the golden dataset.

Offline (default): replays recorded model outputs from fixtures/ for the prompt versions shipped with the lab.
LIVE_EVAL=1: calls the model for real (RECORD_FIXTURES=1 also saves those outputs as new fixtures).
An edited prompt has no fixture, so offline it fails closed: a gate must never pass a prompt nobody evaluated.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
from datetime import date
from functools import lru_cache
from pathlib import Path
from typing import NamedTuple

import pytest
from dotenv import load_dotenv
from pydantic import BaseModel, Field, ValidationError

# Same definitions as Lab 1: what counts as an abstention, how document IDs look, and the judge you calibrated.
from lab1_evals_and_judge.judge_starter import (ABSTENTION, DOC_ID, JUDGE_SYSTEM_PROMPT, llm_judge, openai_client,
                                                parallel_map, wilson_interval)

LAB_DIR = Path(__file__).parent
load_dotenv(LAB_DIR.parent / ".env")  # OPENAI_API_KEY / OPENAI_MODEL for LIVE_EVAL=1

BASELINE = LAB_DIR / "prompt_baseline.txt"
CANDIDATE = (LAB_DIR / os.getenv("PROMPT_CANDIDATE", "prompt_candidate_regressed.txt")).resolve()
FIXTURES = LAB_DIR / "fixtures"
MIN_PASS_RATE = 0.90   # absolute bar for the whole dataset
MAX_SLICE_DROP = 0.05  # the candidate may be at most 5 points below the baseline on any slice

# A single ```json ... ``` block anywhere in the output (models often add a preamble).
FENCED_JSON = re.compile(r"```(?:json)?\s*\n(.*?)```", re.DOTALL)


class SupportResponse(BaseModel):
    answer: str = Field(min_length=1)
    citations: list[str]


class Result(NamedTuple):
    schema_ok: bool
    correct: bool
    reason: str
    answer: str


def load_rows() -> list[dict]:
    # golden_dataset.jsonl uses promptfoo's test-case format: {"description": ..., "vars": {...}}
    lines = (LAB_DIR / "golden_dataset.jsonl").read_text().splitlines()
    return [json.loads(line)["vars"] for line in lines if line.strip()]


def render_prompt(template: str, row: dict) -> str:
    """Fill `{{context}}` / `{{query}}` exactly like promptfoo does, so both runners see the same prompt."""
    return template.replace("{{context}}", row["context"]).replace("{{query}}", row["query"])


def parse_json_output(raw: str) -> dict:
    """Parse model output as JSON. If it contains a fenced ```json block, parse that block.

    Keep this in sync with the javascript assertion in promptfooconfig.yaml.
    """
    match = FENCED_JSON.search(raw)
    return json.loads(match.group(1) if match else raw.strip())


def call_model(prompt_text: str, row: dict) -> str:
    resp = openai_client().chat.completions.create(
        model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        temperature=0,
        messages=[{"role": "user", "content": render_prompt(prompt_text, row)}],
    )
    return resp.choices[0].message.content or ""


@lru_cache(maxsize=None)
def get_outputs(prompt_path: Path) -> dict[str, str]:
    digest = hashlib.sha256(prompt_path.read_bytes()).hexdigest()
    fixture_path = FIXTURES / f"{prompt_path.stem}.json"
    if os.getenv("LIVE_EVAL") == "1":
        prompt_text = prompt_path.read_text()
        rows = load_rows()
        outputs = dict(zip([row["id"] for row in rows], parallel_map(lambda row: call_model(prompt_text, row), rows)))
        if os.getenv("RECORD_FIXTURES") == "1":
            model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
            fixture_path.write_text(json.dumps({
                "prompt_file": prompt_path.name,
                "prompt_sha256": digest,
                "source": f"recorded from {model} on {date.today().isoformat()}",
                "outputs": outputs,
            }, indent=2) + "\n")
        return outputs
    if not fixture_path.exists():
        pytest.fail(f"No recorded outputs for {prompt_path.name}. Offline mode only replays fixtures; "
                    f"evaluate this prompt with LIVE_EVAL=1.")
    fixture = json.loads(fixture_path.read_text())
    if fixture["prompt_sha256"] != digest:
        pytest.fail(f"{prompt_path.name} changed since its outputs were recorded, so offline replay would test "
                    f"a different prompt. Evaluate it with LIVE_EVAL=1 (add RECORD_FIXTURES=1 to save the outputs).")
    return fixture["outputs"]


def score_row(row: dict, raw: str) -> Result:
    """Deterministic checks only. Semantic faithfulness is the live judge's job (last test)."""
    try:
        parsed = SupportResponse.model_validate(parse_json_output(raw))
    except (json.JSONDecodeError, ValidationError):
        return Result(False, False, "invalid JSON or schema", raw[:160])
    known_ids = set(DOC_ID.findall(row["context"]))
    unknown = [c for c in parsed.citations if c not in known_ids]
    if unknown:
        return Result(True, False, f"cites IDs that are not in the context: {unknown}", parsed.answer)
    if row["slice"] == "not_covered":
        # An abstention cites nothing: an answer with citations claims the documents cover the question,
        # whatever phrase it also contains ("not covered on Starter, so students get 50% off Pro").
        abstains = bool(ABSTENTION.search(parsed.answer)) and not parsed.citations
        return Result(True, abstains, "abstained" if abstains else "answered a question the context does not cover",
                      parsed.answer)
    if row["must_contain"].lower() not in parsed.answer.lower():
        return Result(True, False, f"missing the expected fact {row['must_contain']!r}", parsed.answer)
    if row["expected_citation"] not in parsed.citations:
        return Result(True, False, f"missing the citation {row['expected_citation']}", parsed.answer)
    return Result(True, True, "ok", parsed.answer)


@lru_cache(maxsize=None)
def results(prompt_path: Path) -> dict[str, Result]:
    outputs = get_outputs(prompt_path)
    return {row["id"]: score_row(row, outputs[row["id"]]) for row in load_rows()}


def pct(k: int, n: int) -> str:
    lo, hi = wilson_interval(k, n)
    return f"{k}/{n} = {k / n:.0%} [95% CI {lo:.0%}-{hi:.0%}]"


def test_baseline_meets_absolute_bar() -> None:
    res = results(BASELINE).values()
    assert all(r.schema_ok for r in res), "Baseline produced invalid JSON"
    passed = sum(r.correct for r in res)
    assert passed / len(res) >= MIN_PASS_RATE, f"Baseline pass rate {pct(passed, len(res))}"


def test_candidate_schema_is_valid() -> None:
    res = results(CANDIDATE)
    broken = [rid for rid, r in res.items() if not r.schema_ok]
    assert not broken, f"REGRESSION: invalid JSON for {broken}"


def test_candidate_overall_pass_rate() -> None:
    """The aggregate bar. On its own it lets a regression in a small slice through (see the next test)."""
    res = list(results(CANDIDATE).values())
    passed = sum(r.correct for r in res)
    assert passed / len(res) >= MIN_PASS_RATE, f"REGRESSION: overall pass rate {pct(passed, len(res))}"


def test_candidate_no_slice_regression() -> None:
    """Paired comparison: same inputs, baseline vs candidate, judged per slice."""
    rows = load_rows()
    base, cand = results(BASELINE), results(CANDIDATE)
    report, regressed = [], []
    for slice_name in sorted({row["slice"] for row in rows}):
        ids = [row["id"] for row in rows if row["slice"] == slice_name]
        b, c = sum(base[i].correct for i in ids), sum(cand[i].correct for i in ids)
        mark = ""
        if c / len(ids) < b / len(ids) - MAX_SLICE_DROP:
            regressed.append(slice_name)
            mark = "  <-- REGRESSION"
        report.append(f"  {slice_name:<12} baseline {pct(b, len(ids))}  candidate {pct(c, len(ids))}{mark}")

    by_id = {row["id"]: row for row in rows}
    flipped = [i for i in by_id if base[i].correct and not cand[i].correct]
    if flipped:
        report.append("\nCases that flipped PASS -> FAIL:")
        for i in flipped:
            report += [f"  {i} [{by_id[i]['slice']}] {by_id[i]['query']}",
                       f"      baseline : {base[i].answer}",
                       f"      candidate: {cand[i].answer}",
                       f"      why      : {cand[i].reason}"]
    header = f"REGRESSION on slice(s) {regressed} (allowed drop: {MAX_SLICE_DROP * 100:.0f} points)\n" if regressed else ""
    assert not regressed, header + "\n".join(report)


def check_faithfulness(rows: list[dict], cand: dict[str, Result], judge) -> str | None:
    """None if the candidate is faithful enough, else the failure report. judge(row, answer) -> (verdict, reasoning).

    Only answers with a valid schema can be judged, so they are the denominator: counting broken outputs
    as faithful inflates the rate (test_candidate_schema_is_valid fails those separately).
    """
    judged = [row for row in rows if cand[row["id"]].schema_ok]
    if not judged:
        return "REGRESSION: no output with a valid schema, so nothing could be judged for faithfulness"
    verdicts = parallel_map(lambda row: judge(row, cand[row["id"]].answer), judged)
    unfaithful = []
    for row, (verdict, reasoning) in zip(judged, verdicts):
        answer = cand[row["id"]].answer
        if verdict == "FAIL":
            unfaithful.append(f"  {row['id']} {row['query']}\n      answer: {answer}\n      judge : {reasoning}")
    faithful = len(judged) - len(unfaithful)
    if faithful / len(judged) >= MIN_PASS_RATE:
        return None
    return f"REGRESSION: faithfulness {pct(faithful, len(judged))}\n" + "\n".join(unfaithful)


@pytest.mark.skipif(os.getenv("LIVE_EVAL") != "1", reason="semantic faithfulness needs a live judge: run with LIVE_EVAL=1")
def test_candidate_faithfulness_live() -> None:
    """Reuses the judge from Lab 1. Point JUDGE_PROMPT_FILE at the prompt you calibrated there."""
    prompt_file = os.getenv("JUDGE_PROMPT_FILE")
    judge_prompt = Path(prompt_file).read_text() if prompt_file else JUDGE_SYSTEM_PROMPT

    def judge(row: dict, answer: str) -> tuple[str, str]:
        return llm_judge("binary", judge_prompt, {"user_query": row["query"], "retrieved_context": row["context"]}, answer)

    problem = check_faithfulness(load_rows(), results(CANDIDATE), judge)
    assert problem is None, problem
