"""Lab 1 Starter: Deterministic Checks + Calibrated LLM-as-a-Judge."""

from __future__ import annotations

import argparse
import json
import os
import re
from pathlib import Path
from typing import Literal

from dotenv import load_dotenv
from pydantic import BaseModel, Field, ValidationError

load_dotenv()


class ExpectedAnswerSchema(BaseModel):
    answer: str = Field(min_length=1)
    citations: list[str] = Field(min_length=1)


class JudgeVerdict(BaseModel):
    reasoning: str = Field(description="Step-by-step comparison of claims against retrieved_context")
    verdict: Literal["PASS", "FAIL"]


def check_deterministic(raw_output: str) -> tuple[bool, str]:
    """Fast, $0 deterministic check before ever calling an LLM judge."""
    try:
        parsed = json.loads(raw_output)
        ExpectedAnswerSchema.model_validate(parsed)
        return True, "ok"
    except (json.JSONDecodeError, ValidationError) as exc:
        return False, f"deterministic_fail: {exc}"


# TODO (Lab 1): Refine this judge prompt so it catches subtle contradictions & unsupported claims.
JUDGE_SYSTEM_PROMPT = """You are a strict Faithfulness Evaluator.
Given a user_query, retrieved_context, and model_answer:
1. List every factual claim in model_answer.
2. Verify whether each claim is directly supported by retrieved_context.
3. If ANY claim contradicts retrieved_context or invents numbers/features not in retrieved_context, verdict MUST be FAIL.
4. Output JSON matching: {"reasoning": "<step-by-step check>", "verdict": "PASS" | "FAIL"}.
"""


def _numbers(text: str) -> set[str]:
    return set(re.findall(r"\d+(?:\.\d+)?", text))


def run_llm_judge(user_query: str, context: str, answer: str, mock: bool = False) -> JudgeVerdict:
    if mock:
        # Offline stand-in for the LLM judge: a crude, generic heuristic (NOT tuned to this dataset).
        # It only catches invented numbers; non-numeric contradictions slip through.
        invented = _numbers(answer) - _numbers(context)
        if invented:
            return JudgeVerdict(reasoning=f"Mock heuristic: numbers not in context: {sorted(invented)}", verdict="FAIL")
        return JudgeVerdict(
            reasoning="Mock heuristic: all numbers appear in context (non-numeric claims were not checked).",
            verdict="PASS",
        )

    from openai import OpenAI

    client = OpenAI()
    model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    response = client.beta.chat.completions.parse(
        model=model,
        temperature=0,
        messages=[
            {"role": "system", "content": JUDGE_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": (
                    f"user_query: {user_query}\n"
                    f"retrieved_context: {context}\n"
                    f"model_answer: {answer}"
                ),
            },
        ],
        response_format=JudgeVerdict,
    )
    parsed = response.choices[0].message.parsed
    assert parsed is not None
    return parsed


def evaluate_split(traces_path: Path, split: str, mock: bool) -> None:
    rows = [json.loads(line) for line in traces_path.read_text().splitlines() if line.strip()]
    target = [r for r in rows if r["split"] == split]

    tp = fp = tn = fn = 0  # Positive class = "FAIL" (we want high recall/precision on catching failures!)
    for row in target:
        det_ok, reason = check_deterministic(row["model_output"])
        if not det_ok:
            pred = "FAIL"
            detail = reason
        else:
            answer_text = json.loads(row["model_output"])["answer"]
            verdict = run_llm_judge(row["user_query"], row["retrieved_context"], answer_text, mock=mock)
            pred = verdict.verdict
            detail = verdict.reasoning

        actual = row["human_label"]
        if pred == "FAIL" and actual == "FAIL":
            tp += 1
        elif pred == "FAIL" and actual == "PASS":
            fp += 1
            print(f"[FP] {row['id']}: predicted FAIL, human PASS | {detail}")
        elif pred == "PASS" and actual == "PASS":
            tn += 1
        else:
            fn += 1
            print(f"[FN] {row['id']}: predicted PASS, human FAIL | {detail}")

    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    print(f"\nSplit={split} (n={len(target)}) | TP={tp} FP={fp} TN={tn} FN={fn}")
    print(f"Failure Detection Precision: {precision:.2%} | Recall: {recall:.2%}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--mock", action="store_true", help="Run without live OpenAI API calls")
    parser.add_argument(
        "--split",
        choices=["dev", "val"],
        default="dev",
        help="Iterate on 'dev'; run 'val' (held-out) only to report the final calibrated numbers",
    )
    args = parser.parse_args()
    evaluate_split(Path(__file__).parent / "traces_sample.jsonl", split=args.split, mock=args.mock)
