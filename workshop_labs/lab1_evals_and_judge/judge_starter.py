"""Lab 1 Starter: deterministic checks + an LLM judge calibrated against human labels.

Every trace carries one human label per failure mode:
    labels.format        valid JSON with "answer" and "citations"
    labels.citation      citations present (unless the answer abstains) and all IDs are in the retrieved context
    labels.faithfulness  every claim is supported by the retrieved context ("not covered" answers count as faithful)
null means "not applicable" (e.g. no citation or faithfulness label when the output is not even JSON).
`human_label` is the overall verdict: FAIL if any failure mode fails.

Each evaluator is scored only against the label of the failure mode it owns. Scoring a faithfulness
judge against the overall label would credit (or blame) it for JSON and citation problems it never checks.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

from dotenv import load_dotenv
from pydantic import BaseModel, Field, ValidationError

load_dotenv()

TRACES_PATH = Path(__file__).parent / "traces_sample.jsonl"
DOC_ID = re.compile(r"\[([A-Z]+-\d+)\]")
# Phrases that mark an answer as "the context does not cover this" (an abstention).
ABSTENTION = re.compile(
    r"\b(?:doesn't|does not|don't|do not)\s+(?:say|state|mention|cover|specify|name)\b"
    r"|\bnot\s+(?:covered|mentioned|specified|documented)\b",
    re.IGNORECASE,
)


class AnswerSchema(BaseModel):
    answer: str = Field(min_length=1)
    citations: list[str]


class JudgeVerdict(BaseModel):
    reasoning: str = Field(description="Claim-by-claim check against retrieved_context, written before the verdict")
    verdict: Literal["PASS", "FAIL"]


class LikertVerdict(BaseModel):
    reasoning: str
    score: Literal[1, 2, 3, 4, 5]


# ---------------------------------------------------------------------------
# Deterministic checks: $0, ~1 ms. Never pay an LLM for what code can check.
# ---------------------------------------------------------------------------


def check_format(raw_output: str) -> tuple[bool, str, AnswerSchema | None]:
    try:
        return True, "ok", AnswerSchema.model_validate(json.loads(raw_output))
    except (json.JSONDecodeError, ValidationError) as exc:
        return False, f"format: {type(exc).__name__}", None


def check_citations(parsed: AnswerSchema, context: str) -> tuple[bool, str]:
    known_ids = set(DOC_ID.findall(context))
    if not parsed.citations:
        if ABSTENTION.search(parsed.answer):
            return True, "abstention without citations"
        return False, "citations: empty for a substantive answer"
    unknown = [c for c in parsed.citations if c not in known_ids]
    if unknown:
        return False, f"citations: not in retrieved context: {unknown}"
    return True, "ok"


# ---------------------------------------------------------------------------
# LLM judges
# ---------------------------------------------------------------------------

# Baseline: the vague 1-5 rubric many teams start with. Run it once (--judge likert) and read where it
# disagrees with the human labels before you work on the binary judge.
LIKERT_JUDGE_PROMPT = """You are evaluating answers from a customer-support assistant.
Rate the overall quality of model_answer from 1 (very poor) to 5 (excellent).
Return JSON: {"reasoning": "<why>", "score": <1-5>}"""
LIKERT_PASS_THRESHOLD = 4  # Where to cut a 1-5 scale into PASS/FAIL is arbitrary. That is part of the problem.

# TODO (Lab 1): After failure analysis on dev, rewrite this prompt so the criteria are explicit:
#   - check the answer claim by claim against retrieved_context,
#   - say what counts as unsupported (invented, contradicted, taken from the wrong document, partly supported),
#   - say how to treat "the documentation doesn't cover this" answers,
#   - keep tone, length and helpfulness out of scope.
JUDGE_SYSTEM_PROMPT = """You are a Faithfulness Evaluator.
Given a user_query, retrieved_context and model_answer, decide whether model_answer is faithful to retrieved_context.
Write your reasoning first, then the verdict.
Return JSON: {"reasoning": "<step-by-step check>", "verdict": "PASS" | "FAIL"}"""


def _numbers(text: str) -> set[str]:
    return set(re.findall(r"\d+(?:\.\d+)?", text))


def mock_judge(context: str, answer: str) -> tuple[str, str]:
    """Offline stand-in: a crude, generic heuristic (NOT tuned to this dataset).

    It only catches numbers that do not appear in the context. Non-numeric inventions,
    inversions and mixed-up documents slip through, so its scores are not a target.
    """
    invented = _numbers(answer) - _numbers(context)
    if invented:
        return "FAIL", f"mock: numbers not in context: {sorted(invented)}"
    return "PASS", "mock: all numbers appear in context (nothing else was checked)"


def llm_judge(kind: str, system_prompt: str, row: dict, answer: str) -> tuple[str, str]:
    from openai import OpenAI

    client = OpenAI()
    messages = [
        {"role": "system", "content": system_prompt},
        {
            "role": "user",
            "content": (
                f"user_query: {row['user_query']}\n"
                f"retrieved_context:\n{row['retrieved_context']}\n"
                f"model_answer: {answer}"
            ),
        },
    ]
    model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    if kind == "likert":
        resp = client.beta.chat.completions.parse(model=model, temperature=0, messages=messages, response_format=LikertVerdict)
        likert = resp.choices[0].message.parsed
        assert likert is not None
        verdict = "PASS" if likert.score >= LIKERT_PASS_THRESHOLD else "FAIL"
        return verdict, f"score={likert.score}: {likert.reasoning}"
    resp = client.beta.chat.completions.parse(model=model, temperature=0, messages=messages, response_format=JudgeVerdict)
    binary = resp.choices[0].message.parsed
    assert binary is not None
    return binary.verdict, binary.reasoning


# ---------------------------------------------------------------------------
# Agreement metrics. Positive class = FAIL: we care about catching failures.
# ---------------------------------------------------------------------------


def wilson_interval(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    """95% Wilson score interval for k successes out of n. Small n -> wide interval."""
    if n == 0:
        return 0.0, 1.0
    p = k / n
    denom = 1 + z * z / n
    center = (p + z * z / (2 * n)) / denom
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return max(0.0, center - half), min(1.0, center + half)


@dataclass
class Agreement:
    name: str
    tp: int = 0
    fp: int = 0
    tn: int = 0
    fn: int = 0
    disagreements: list[str] = field(default_factory=list)

    def add(self, row: dict, predicted: str, actual: str, detail: str) -> None:
        if predicted == "FAIL" and actual == "FAIL":
            self.tp += 1
        elif predicted == "FAIL" and actual == "PASS":
            self.fp += 1
            self.disagreements.append(f"[FP] {row['id']}: predicted FAIL, human PASS | {detail}")
        elif predicted == "PASS" and actual == "PASS":
            self.tn += 1
        else:
            self.fn += 1
            self.disagreements.append(f"[FN] {row['id']}: predicted PASS, human FAIL ({row['failure_note']}) | {detail}")

    def kappa(self) -> float:
        n = self.tp + self.fp + self.tn + self.fn
        if n == 0:
            return float("nan")
        observed = (self.tp + self.tn) / n
        expected = ((self.tp + self.fp) * (self.tp + self.fn) + (self.tn + self.fn) * (self.tn + self.fp)) / (n * n)
        return 1.0 if expected == 1 else (observed - expected) / (1 - expected)

    def row(self) -> str:
        def rate(k: int, n: int) -> str:
            if n == 0:
                return f"{'n/a':>22}"
            lo, hi = wilson_interval(k, n)
            return f"{k / n:6.1%} [{lo:5.1%}-{hi:6.1%}]"

        n = self.tp + self.fp + self.tn + self.fn
        precision = rate(self.tp, self.tp + self.fp)
        recall = rate(self.tp, self.tp + self.fn)
        return (
            f"{self.name:<32}{n:>3}{self.tp:>4}{self.fp:>4}{self.tn:>4}{self.fn:>4}  "
            f"{precision}  {recall}  {self.kappa():5.2f}"
        )


def evaluate_split(split: str, judge: str, judge_prompt: str, mock: bool) -> None:
    rows = [json.loads(line) for line in TRACES_PATH.read_text().splitlines() if line.strip()]
    target = [r for r in rows if r["split"] == split]
    judge_name = f"faithfulness judge ({'mock' if mock else judge})"
    fmt, cit, faith, e2e = (Agreement("format check (code)"), Agreement("citation check (code)"),
                            Agreement(judge_name), Agreement("end-to-end vs human_label"))

    for row in target:
        labels = row["labels"]
        fmt_ok, fmt_detail, parsed = check_format(row["model_output"])
        fmt.add(row, "PASS" if fmt_ok else "FAIL", labels["format"], fmt_detail)
        pipeline = "PASS" if fmt_ok else "FAIL"

        if parsed is not None:
            cit_ok, cit_detail = check_citations(parsed, row["retrieved_context"])
            if labels["citation"] is not None:
                cit.add(row, "PASS" if cit_ok else "FAIL", labels["citation"], cit_detail)
            if mock:
                verdict, reasoning = mock_judge(row["retrieved_context"], parsed.answer)
            else:
                verdict, reasoning = llm_judge(judge, judge_prompt, row, parsed.answer)
            if labels["faithfulness"] is not None:
                faith.add(row, verdict, labels["faithfulness"], reasoning)
            pipeline = "FAIL" if (not cit_ok or verdict == "FAIL") else "PASS"

        e2e.add(row, pipeline, row["human_label"], "first failing evaluator decides")

    print(f"Split={split} (n={len(target)}). Positive class = FAIL. Intervals are 95% Wilson CIs.\n")
    print(f"{'Evaluator':<32}{'n':>3}{'TP':>4}{'FP':>4}{'TN':>4}{'FN':>4}  {'Precision [95% CI]':<22}  {'Recall [95% CI]':<22}  kappa")
    for agreement in (fmt, cit, faith, e2e):
        print(agreement.row())
    for agreement in (fmt, cit, faith):
        if agreement.disagreements:
            print(f"\nDisagreements: {agreement.name}")
            for line in agreement.disagreements:
                print("  " + line)
    print("\nWith this few labels the intervals are wide: read the disagreements, not just the scores.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--mock", action="store_true", help="No API calls: the faithfulness judge becomes a crude numeric heuristic")
    parser.add_argument("--split", choices=["dev", "val"], default="dev",
                        help="Iterate on 'dev'; run 'val' (held-out) only once your judge prompt is frozen")
    parser.add_argument("--judge", choices=["binary", "likert"], default="binary",
                        help="'likert' runs the vague 1-5 baseline rubric for comparison")
    parser.add_argument("--judge-prompt", type=Path,
                        help="Load the binary judge prompt from a file (e.g. solutions/lab1_judge_prompt.txt)")
    args = parser.parse_args()
    if args.mock and args.judge == "likert":
        parser.error("--judge likert needs a live model; there is no offline stand-in for a vague rubric")
    if args.judge_prompt and args.judge == "likert":
        parser.error("--judge-prompt replaces the binary judge prompt; it cannot be combined with --judge likert")
    prompt = LIKERT_JUDGE_PROMPT if args.judge == "likert" else JUDGE_SYSTEM_PROMPT
    if args.judge_prompt:
        prompt = args.judge_prompt.read_text()
    evaluate_split(args.split, args.judge, prompt, args.mock)
