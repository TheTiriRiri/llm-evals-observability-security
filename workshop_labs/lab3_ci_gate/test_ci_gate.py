"""Lab 3 CI Regression Gate: enforces 100% schema validity and >=90% faithfulness."""

from __future__ import annotations

import json
import os
import re
from pathlib import Path

from dotenv import load_dotenv
from pydantic import BaseModel, Field, ValidationError

LAB_DIR = Path(__file__).parent
load_dotenv(LAB_DIR.parent / ".env")  # OPENAI_API_KEY / OPENAI_MODEL for LIVE_EVAL=1

# A single ```json ... ``` block anywhere in the output (models often add a preamble).
FENCED_JSON = re.compile(r"```(?:json)?\s*\n(.*?)```", re.DOTALL)


class SupportResponse(BaseModel):
    answer: str = Field(min_length=1)
    citations: list[str] = Field(min_length=1)


def render_prompt(template: str, row: dict) -> str:
    """Fill `{{context}}` / `{{query}}` exactly like promptfoo does, so both runners see the same prompt."""
    return template.replace("{{context}}", row["context"]).replace("{{query}}", row["query"])


def parse_json_output(raw: str) -> dict:
    """Parse model output as JSON. If it contains a fenced ```json block, parse that block.

    Keep this in sync with the javascript assertion in promptfooconfig.yaml.
    """
    match = FENCED_JSON.search(raw)
    return json.loads(match.group(1) if match else raw.strip())


def simulate_model_call(prompt_text: str, row: dict) -> str:
    """Uses live OpenAI if LIVE_EVAL=1, otherwise simulates prompt behavior deterministically."""
    if os.getenv("LIVE_EVAL") == "1":
        from openai import OpenAI
        client = OpenAI()
        resp = client.chat.completions.create(
            model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            temperature=0,
            messages=[{"role": "user", "content": render_prompt(prompt_text, row)}],
        )
        return resp.choices[0].message.content or ""

    # Deterministic simulation reflecting whether the prompt enforces JSON + citations
    if "JSON" in prompt_text and "citations" in prompt_text:
        return json.dumps({
            "answer": f"Based on policy, {row['must_contain']} applies.",
            "citations": [row["expected_citation"]],
        })
    return f"Hi there! Happy to help! Regarding your question, {row['must_contain']} applies. Have a great day!"


def evaluate_prompt(prompt_file: str) -> tuple[float, float]:
    prompt_text = (LAB_DIR / prompt_file).read_text()
    # golden_dataset.jsonl uses promptfoo's test-case format: {"description": ..., "vars": {...}}
    rows = [json.loads(line)["vars"] for line in (LAB_DIR / "golden_dataset.jsonl").read_text().splitlines() if line.strip()]

    schema_passes = 0
    grounded_passes = 0
    for row in rows:
        raw = simulate_model_call(prompt_text, row)
        try:
            parsed = SupportResponse.model_validate(parse_json_output(raw))
            schema_passes += 1
            if row["must_contain"].lower() in parsed.answer.lower() and row["expected_citation"] in parsed.citations:
                grounded_passes += 1
        except (json.JSONDecodeError, ValidationError):
            pass

    n = len(rows)
    return schema_passes / n, grounded_passes / n


def test_baseline_passes_ci_gate() -> None:
    schema_rate, grounded_rate = evaluate_prompt("prompt_baseline.txt")
    assert schema_rate == 1.0, f"Schema validity dropped to {schema_rate:.0%}"
    assert grounded_rate >= 0.90, f"Groundedness dropped to {grounded_rate:.0%}"


def test_candidate_passes_ci_gate() -> None:
    """This test MUST FAIL until participants fix prompt_candidate_regressed.txt!"""
    schema_rate, grounded_rate = evaluate_prompt("prompt_candidate_regressed.txt")
    assert schema_rate == 1.0, f"REGRESSION: Schema validity is {schema_rate:.0%} (expected 100%)"
    assert grounded_rate >= 0.90, f"REGRESSION: Groundedness is {grounded_rate:.0%} (expected >=90%)"
