"""Lab 2 Starter: Multi-step RAG + Tool Agent with planted latency & cost bottlenecks."""

from __future__ import annotations

import json
import os
import time
import uuid
from contextlib import ExitStack, contextmanager
from dataclasses import asdict, dataclass, field
from typing import Any, Iterator

from dotenv import load_dotenv

load_dotenv()

PROMPT_VERSION = "v1.2.0"
MODEL_NAME = os.getenv("OPENAI_MODEL", "gpt-4o-mini")


# ---------------------------------------------------------------------------
# Tracing plumbing (you do not need to change this part)
# ---------------------------------------------------------------------------


@dataclass
class SpanRecord:
    name: str
    duration_ms: float
    attributes: dict = field(default_factory=dict)


class LocalTraceCollector:
    """Fallback trace collector, always on; mirrors what is sent to Langfuse."""

    def __init__(self, trace_id: str) -> None:
        self.trace_id = trace_id
        self.spans: list[SpanRecord] = []
        self.scores: list[dict] = []

    def add_span(self, name: str, duration_ms: float, **attrs: Any) -> None:
        self.spans.append(SpanRecord(name=name, duration_ms=round(duration_ms, 2), attributes=attrs))

    def score(self, name: str, value: float) -> None:
        self.scores.append({"name": name, "value": value})

    def dump(self) -> None:
        print(json.dumps({"trace_id": self.trace_id, "spans": [asdict(s) for s in self.spans], "scores": self.scores}, indent=2))


def langfuse_configured() -> bool:
    """Both keys must be real values; the .env.example placeholders count as unset."""
    public = os.getenv("LANGFUSE_PUBLIC_KEY", "")
    secret = os.getenv("LANGFUSE_SECRET_KEY", "")
    return bool(public and secret) and not public.startswith("pk-lf-your") and not secret.startswith("sk-lf-your")


class SpanHandle:
    """Collects attributes for one span while the step runs."""

    def __init__(self, attrs: dict) -> None:
        self.attrs = attrs

    def set(self, **attrs: Any) -> None:
        self.attrs.update(attrs)


class Tracer:
    """Records every span locally and, when Langfuse keys are set, as nested Langfuse observations.

    Uses the OpenTelemetry-based Langfuse SDK (v5): one root observation per request,
    child observations opened with `start_as_current_observation`, and an explicit
    `flush()` so short-lived scripts do not exit before spans are exported.
    """

    def __init__(self, user_id: str) -> None:
        self.user_id = user_id
        self._lf = None
        if langfuse_configured():
            from langfuse import Langfuse

            self._lf = Langfuse()
            trace_id = Langfuse.create_trace_id()
        else:
            trace_id = uuid.uuid4().hex
        self.collector = LocalTraceCollector(trace_id)

    @contextmanager
    def trace(self, name: str, **metadata: Any) -> Iterator[None]:
        """Root of the trace. All `span()` calls must happen inside this block."""
        with ExitStack() as stack:
            if self._lf is not None:
                from langfuse import propagate_attributes

                stack.enter_context(
                    propagate_attributes(
                        user_id=self.user_id,
                        trace_name=name,
                        metadata={k: str(v) for k, v in metadata.items()},
                    )
                )
                stack.enter_context(
                    self._lf.start_as_current_observation(
                        name=name,
                        as_type="agent",
                        trace_context={"trace_id": self.collector.trace_id},
                        metadata=metadata,
                    )
                )
            yield

    @contextmanager
    def span(self, name: str, as_type: str = "span", **attrs: Any) -> Iterator[SpanHandle]:
        """Time one step. Add attributes during the step with `handle.set(key=value)`.

        For `as_type="generation"`, set `gen_ai.request.model` and
        `gen_ai.usage.input_tokens` (OpenTelemetry GenAI semantic conventions);
        they are forwarded to Langfuse as model + usage so cost is computed.
        """
        handle = SpanHandle(dict(attrs))
        t0 = time.perf_counter()
        with ExitStack() as stack:
            obs = None
            if self._lf is not None:
                obs = stack.enter_context(self._lf.start_as_current_observation(name=name, as_type=as_type))
            yield handle
            duration_ms = (time.perf_counter() - t0) * 1000
            if obs is not None:
                extra: dict[str, Any] = {}
                if as_type == "generation":
                    if "gen_ai.request.model" in handle.attrs:
                        extra["model"] = handle.attrs["gen_ai.request.model"]
                    if "gen_ai.usage.input_tokens" in handle.attrs:
                        extra["usage_details"] = {"input": int(handle.attrs["gen_ai.usage.input_tokens"])}
                obs.update(metadata=handle.attrs, **extra)
        self.collector.add_span(name, duration_ms, **handle.attrs)

    def score(self, name: str, value: float) -> None:
        """Attach a score (e.g. user feedback) to the current trace. Call inside `trace()`."""
        self.collector.score(name, value)
        if self._lf is not None:
            self._lf.score_current_trace(name=name, value=value)

    def finish(self) -> None:
        # Local trace first: a Langfuse problem (wrong keys, host down) must not hide the result.
        self.collector.dump()
        if self._lf is not None:
            self._lf.flush()
            try:
                print(f"Langfuse trace: {self._lf.get_trace_url(trace_id=self.collector.trace_id)}")
            except Exception as exc:  # noqa: BLE001 - diagnostics only
                print(f"Langfuse trace URL unavailable ({type(exc).__name__}: {exc}). Check LANGFUSE_* keys and LANGFUSE_HOST.")


# ---------------------------------------------------------------------------
# The agent (this is what you diagnose and fix)
# ---------------------------------------------------------------------------


def retrieve_docs(query: str, k: int = 20) -> list[dict]:
    """BOTTLENECK 1: k=20 stuffs ~2,000 tokens of mostly irrelevant chunks into the prompt."""
    time.sleep(0.12)  # simulated vector DB latency
    docs = [{"id": f"doc-{i}", "text": f"Chunk {i} policy details... " * 25} for i in range(k)]
    return docs


def fetch_customer_tier(user_id: str) -> str:
    time.sleep(0.65)  # simulated CRM HTTP call
    return "enterprise"


def fetch_billing_status(user_id: str) -> str:
    time.sleep(0.65)  # simulated Billing HTTP call
    return "active"


def synthesize_answer(query: str, docs: list[dict], tier: str, status: str) -> tuple[str, int]:
    context_tokens = sum(len(d["text"].split()) for d in docs)
    time.sleep(0.25)  # simulated LLM TTFT + generation
    answer = f"[{tier}/{status}] Based on {docs[0]['id']}, refunds are valid within 14 days."
    return answer, context_tokens


def run_agent(user_id: str, query: str) -> None:
    tracer = Tracer(user_id=user_id)

    with tracer.trace("support-rag-agent", prompt_version=PROMPT_VERSION):
        # Step 1: Retrieval
        with tracer.span("vector_retrieval", as_type="retriever") as span:
            docs = retrieve_docs(query, k=20)  # TODO (Lab 2): Tune k and add retrieval_k metadata
            span.set(doc_count=len(docs))

        # Step 2: Tool calls (BOTTLENECK 2: sequential independent I/O!)
        # TODO (Lab 2): Parallelize fetch_customer_tier and fetch_billing_status using ThreadPoolExecutor.
        # Note: OpenTelemetry context does not follow work into threads, so keep the span
        # in this (main) thread and run only the plain functions in the pool.
        with tracer.span("tool_fetch_customer_tier", as_type="tool"):
            tier = fetch_customer_tier(user_id)

        with tracer.span("tool_fetch_billing_status", as_type="tool"):
            status = fetch_billing_status(user_id)

        # Step 3: LLM Synthesis
        with tracer.span("llm_synthesis", as_type="generation") as span:
            answer, input_tokens = synthesize_answer(query, docs, tier, status)
            span.set(**{"gen_ai.request.model": MODEL_NAME, "gen_ai.usage.input_tokens": input_tokens})
            # TODO (Lab 2): Attach prompt_version and user_tier to this span!

        # TODO (Lab 2): Attach a user feedback score (e.g., tracer.score("user_thumbs_up", 1.0))

    print(f"Answer: {answer}\n")
    tracer.finish()


if __name__ == "__main__":
    run_agent(user_id="usr_42", query="What is the refund window?")
