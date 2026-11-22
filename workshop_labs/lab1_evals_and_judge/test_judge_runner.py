"""Lab 1: tests of the judge runner itself (offline: the OpenAI client is replaced by a stand-in)."""

import threading
import time
from types import SimpleNamespace

import openai
import pytest

from lab1_evals_and_judge import judge_starter as js


class Concurrency:
    """Counts how many calls are in flight at once."""

    def __init__(self) -> None:
        self.active = self.peak = 0
        self._lock = threading.Lock()

    def __enter__(self) -> None:
        with self._lock:
            self.active += 1
            self.peak = max(self.peak, self.active)

    def __exit__(self, *_: object) -> None:
        with self._lock:
            self.active -= 1


class FakeOpenAI:
    """Has only the stable chat.completions.parse API, no `beta`. Records its constructor arguments."""

    created: list[dict] = []
    calls = Concurrency()

    def __init__(self, **kwargs: object) -> None:
        FakeOpenAI.created.append(kwargs)
        self.chat = SimpleNamespace(completions=SimpleNamespace(parse=self._parse))

    def _parse(self, *, response_format, **_: object):
        with FakeOpenAI.calls:
            time.sleep(0.02)
        parsed = response_format(reasoning="scripted", verdict="PASS")
        return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(parsed=parsed))])


@pytest.fixture
def fake_openai(monkeypatch):
    FakeOpenAI.created, FakeOpenAI.calls = [], Concurrency()
    monkeypatch.setattr(openai, "OpenAI", FakeOpenAI)
    if hasattr(js, "openai_client"):
        js.openai_client.cache_clear()
    yield FakeOpenAI
    if hasattr(js, "openai_client"):
        js.openai_client.cache_clear()


ROW = {"user_query": "q", "retrieved_context": "[P-1] c"}


def test_llm_judge_uses_the_stable_parse_api(fake_openai) -> None:
    assert js.llm_judge("binary", "system", ROW, "answer") == ("PASS", "scripted")


def test_live_client_retries_and_is_shared(fake_openai) -> None:
    """One client for all judge calls, with retries for 429s on a shared or per-person key."""
    js.llm_judge("binary", "system", ROW, "a")
    js.llm_judge("binary", "system", ROW, "b")
    assert len(fake_openai.created) == 1
    assert fake_openai.created[0].get("max_retries", 2) >= 5


def test_live_judge_calls_overlap(fake_openai, capsys) -> None:
    """20 sequential round trips are most of the lab's waiting time; a few workers cut it."""
    js.evaluate_split("dev", "binary", js.JUDGE_SYSTEM_PROMPT, mock=False)
    assert fake_openai.calls.peak > 1


def test_parallel_map_keeps_input_order() -> None:
    def slow_double(x: int) -> int:
        time.sleep(0.01 * (5 - x % 5))  # later items finish first
        return 2 * x

    assert js.parallel_map(slow_double, range(10)) == [2 * x for x in range(10)]


def test_show_prints_one_trace_in_full(capsys) -> None:
    js.show_trace("t02")
    out = capsys.readouterr().out
    row = next(r for r in js.load_traces() if r["id"] == "t02")
    for part in (row["user_query"], row["retrieved_context"], row["model_output"], row["human_label"]):
        assert part in out
