"""Lab 3: tests of the gate's own scoring rules. A gate that scores wrongly passes the wrong prompts.

These run offline and stay green whatever prompt you test; test_ci_gate.py is the gate itself.
"""

import json
import threading
import time

import lab3_ci_gate.test_ci_gate as gate
from lab3_ci_gate.test_ci_gate import Result, check_faithfulness, load_rows, score_row

ROWS = load_rows()
NOT_COVERED = next(r for r in ROWS if r["id"] == "g20")  # "Is there a student discount?"


def output(answer: str, citations: list[str]) -> str:
    return json.dumps({"answer": answer, "citations": citations})


def test_not_covered_answer_with_a_citation_is_not_an_abstention() -> None:
    """The abstention phrase alone is not enough: an answer that cites a document claims the docs cover it."""
    raw = output("Student discounts are not covered on Starter, so students get 50% off Pro.", ["P-05"])
    assert not score_row(NOT_COVERED, raw).correct


def test_not_covered_abstention_without_citations_passes() -> None:
    """Utility twin: the honest answer still passes."""
    raw = output("The documentation does not mention a student discount.", [])
    assert score_row(NOT_COVERED, raw).correct


def judge_says(verdicts: dict[str, str]):
    return lambda row, answer: (verdicts.get(row["id"], "PASS"), "scripted")


def test_faithfulness_counts_only_answers_it_judged() -> None:
    """18 valid answers, 2 of them unfaithful = 89%, below the bar. Counting 2 broken outputs as faithful made it 90%."""
    cand = {r["id"]: Result(True, True, "ok", "an answer") for r in ROWS}
    cand["g01"] = cand["g02"] = Result(False, False, "invalid JSON or schema", "")
    problem = check_faithfulness(ROWS, cand, judge_says({"g03": "FAIL", "g04": "FAIL"}))
    assert problem is not None and "16/18" in problem


def test_faithfulness_fails_when_nothing_could_be_judged() -> None:
    cand = {r["id"]: Result(False, False, "invalid JSON or schema", "") for r in ROWS}
    assert check_faithfulness(ROWS, cand, judge_says({})) is not None


def test_faithfulness_passes_a_faithful_candidate() -> None:
    cand = {r["id"]: Result(True, True, "ok", "an answer") for r in ROWS}
    assert check_faithfulness(ROWS, cand, judge_says({})) is None


class Peak:
    """Wraps a function and records how many calls were in flight at once."""

    def __init__(self, fn) -> None:
        self.fn, self.active, self.peak, self._lock = fn, 0, 0, threading.Lock()

    def __call__(self, *args):
        with self._lock:
            self.active += 1
            self.peak = max(self.peak, self.active)
        time.sleep(0.02)
        try:
            return self.fn(*args)
        finally:
            with self._lock:
                self.active -= 1


def test_live_outputs_are_collected_concurrently_and_keyed_by_row(monkeypatch, tmp_path) -> None:
    """LIVE_EVAL=1 makes 20 model calls; they overlap, and each output still lands on its own row."""
    monkeypatch.setenv("LIVE_EVAL", "1")
    monkeypatch.delenv("RECORD_FIXTURES", raising=False)
    model = Peak(lambda prompt_text, row: f"output for {row['id']}")
    monkeypatch.setattr(gate, "call_model", model)
    prompt = tmp_path / "prompt_under_test.txt"
    prompt.write_text("{{context}}\n{{query}}")

    assert gate.get_outputs(prompt) == {r["id"]: f"output for {r['id']}" for r in ROWS}
    assert model.peak > 1


def test_faithfulness_judge_calls_overlap() -> None:
    cand = {r["id"]: Result(True, True, "ok", "an answer") for r in ROWS}
    judge = Peak(lambda row, answer: ("PASS", "scripted"))
    assert check_faithfulness(ROWS, cand, judge) is None
    assert judge.peak > 1
