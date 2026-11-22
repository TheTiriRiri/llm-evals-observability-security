"""Lab 2: what the tracing plumbing records, for the starter and the solution (offline, simulated latency)."""

import sys

import langfuse
import pytest

from lab2_observability import slow_rag_agent as agent
from solutions.lab2_fast_rag_agent import run_fast_agent


@pytest.fixture(autouse=True)
def local_tracing_only(monkeypatch):
    """Tests never export to a real Langfuse project, whatever .env says."""
    monkeypatch.delenv("LANGFUSE_PUBLIC_KEY", raising=False)
    monkeypatch.delenv("LANGFUSE_SECRET_KEY", raising=False)
    if hasattr(agent._langfuse, "cache_clear"):
        agent._langfuse.cache_clear()
    yield
    if hasattr(agent._langfuse, "cache_clear"):
        agent._langfuse.cache_clear()


def spans(tracer) -> dict[str, dict]:
    return {s.name: s.attributes for s in tracer.collector.spans}


@pytest.mark.parametrize("run", [agent.run_agent, run_fast_agent], ids=["starter", "solution"])
def test_generation_spans_carry_the_required_genai_attributes(run) -> None:
    """OpenTelemetry GenAI conventions: operation and provider are required on client spans."""
    _, tracer = run("usr_1", agent.DEMO_QUERY, 0)
    for name in ("query_rewrite", "llm_synthesis"):
        attrs = spans(tracer)[name]
        assert attrs["gen_ai.operation.name"] == "chat", name
        assert attrs["gen_ai.provider.name"] == "openai", name
        assert attrs["gen_ai.request.model"] == attrs["gen_ai.response.model"] == agent.MODEL_NAME, name


def test_solution_records_retrieval_hit_before_and_after_rerank() -> None:
    """Hit at k=20 and hit after the top-4 cut are different questions: record both."""
    _, tracer = run_fast_agent("usr_1", agent.DEMO_QUERY, 0)
    assert spans(tracer)["vector_retrieval"]["retrieval_hit"] is True
    assert spans(tracer)["rerank"]["retrieval_hit"] is True


class FakeLangfuse:
    instances = 0
    flushes = 0

    def __init__(self, **_: object) -> None:
        FakeLangfuse.instances += 1

    def create_trace_id(self) -> str:
        return "0" * 32

    def flush(self) -> None:
        FakeLangfuse.flushes += 1


def test_one_langfuse_client_and_one_flush_per_run(monkeypatch) -> None:
    """A flush per request blocks the loop on the network; the SDK batches, so flush once before exit."""
    FakeLangfuse.instances = FakeLangfuse.flushes = 0
    monkeypatch.setenv("LANGFUSE_PUBLIC_KEY", "pk-lf-test")
    monkeypatch.setenv("LANGFUSE_SECRET_KEY", "sk-lf-test")
    monkeypatch.setattr(langfuse, "Langfuse", FakeLangfuse)
    monkeypatch.setattr(sys, "argv", ["slow_rag_agent.py", "--requests", "3"])

    agent.main(run=lambda user_id, query, i: ("ok", agent.Tracer(user_id)))

    assert (FakeLangfuse.instances, FakeLangfuse.flushes) == (1, 1)
