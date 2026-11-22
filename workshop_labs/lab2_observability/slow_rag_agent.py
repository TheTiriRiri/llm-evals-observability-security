"""Lab 2 Starter: multi-step RAG + tool agent with planted latency, cost and retrieval traps."""

from __future__ import annotations

import argparse
import json
import math
import os
import re
import time
import uuid
from contextlib import ExitStack, contextmanager
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone
from functools import lru_cache
from typing import Any, Callable, Iterator

from dotenv import load_dotenv

load_dotenv()

PROMPT_VERSION = "v1.2.0"
MODEL_NAME = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
DEMO_QUERY = "What is the refund window for annual plans? Please reply to jane.doe@example.com"
# Ground truth for the demo query: the document that answers it. In production you measure
# retrieval quality (recall@k) offline on a labeled set; here we know the answer for one query.
EXPECTED_DOC_ID = "P-101"


# ---------------------------------------------------------------------------
# Tracing plumbing (you do not need to change this part)
# ---------------------------------------------------------------------------

EMAIL = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")


def mask_pii(*, data: Any, **kwargs: Any) -> Any:
    """Masks e-mail addresses in everything the tracer records (Langfuse `mask=` hook signature).

    Traces hold raw prompts and retrieved documents. Mask before they leave the process (Day 2, Lab 5).
    """
    if isinstance(data, str):
        return EMAIL.sub("<EMAIL>", data)
    if isinstance(data, dict):
        return {k: mask_pii(data=v) for k, v in data.items()}
    if isinstance(data, list):
        return [mask_pii(data=v) for v in data]
    return data


@dataclass
class SpanRecord:
    name: str
    duration_ms: float
    attributes: dict = field(default_factory=dict)


class LocalTraceCollector:
    """Fallback trace collector, always on; mirrors what is sent to Langfuse."""

    def __init__(self, trace_id: str) -> None:
        self.trace_id = trace_id
        self.input: str | None = None
        self.spans: list[SpanRecord] = []
        self.total_ms = 0.0

    def add_span(self, name: str, duration_ms: float, **attrs: Any) -> None:
        self.spans.append(SpanRecord(name=name, duration_ms=round(duration_ms, 2), attributes=mask_pii(data=attrs)))

    def dump(self) -> None:
        print(json.dumps({"trace_id": self.trace_id, "input": self.input, "total_ms": round(self.total_ms, 2),
                          "spans": [asdict(s) for s in self.spans]}, indent=2))


def langfuse_configured() -> bool:
    """Both keys must be real values; the .env.example placeholders count as unset."""
    public = os.getenv("LANGFUSE_PUBLIC_KEY", "")
    secret = os.getenv("LANGFUSE_SECRET_KEY", "")
    return bool(public and secret) and not public.startswith("pk-lf-your") and not secret.startswith("sk-lf-your")


@lru_cache(maxsize=1)
def _langfuse():
    """One client per process. The SDK batches spans in the background; flush_traces() sends the rest before exit."""
    from langfuse import Langfuse

    return Langfuse(mask=mask_pii)


class SpanHandle:
    """Collects attributes for one span while the step runs."""

    def __init__(self, attrs: dict) -> None:
        self.attrs = attrs

    def set(self, **attrs: Any) -> None:
        self.attrs.update(attrs)


class Tracer:
    """Records every span locally and, when Langfuse keys are set, as nested Langfuse observations.

    Uses the OpenTelemetry-based Langfuse SDK (v5): one root observation per request and
    child observations opened with `start_as_current_observation`. The runner calls
    flush_traces() once at the end, so a short-lived script does not exit before spans are exported.
    """

    def __init__(self, user_id: str) -> None:
        self.user_id = user_id
        self._lf = _langfuse() if langfuse_configured() else None
        trace_id = self._lf.create_trace_id() if self._lf is not None else uuid.uuid4().hex
        self.collector = LocalTraceCollector(trace_id)

    @property
    def trace_id(self) -> str:
        return self.collector.trace_id

    @contextmanager
    def trace(self, name: str, input: str, **metadata: Any) -> Iterator[None]:
        """Root of the trace. All `span()` calls must happen inside this block."""
        self.collector.input = mask_pii(data=input)
        t0 = time.perf_counter()
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
                        trace_context={"trace_id": self.trace_id},
                        input=input,
                        metadata=metadata,
                    )
                )
            yield
        self.collector.total_ms = (time.perf_counter() - t0) * 1000

    @contextmanager
    def span(self, name: str, as_type: str = "span", **attrs: Any) -> Iterator[SpanHandle]:
        """Time one step. Add attributes during the step with `handle.set(key=value)`.

        For `as_type="generation"`, set the OpenTelemetry GenAI attributes from genai_attributes()
        (plus `ttft_ms` if you have it). This tracer copies the model, the token usage and the time
        to first token into Langfuse's own fields, so Langfuse can compute cost and TTFT.
        """
        handle = SpanHandle(dict(attrs))
        started_at = datetime.now(timezone.utc)
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
                    # Cost follows the model that answered (response), which can differ from the one requested.
                    model = handle.attrs.get("gen_ai.response.model") or handle.attrs.get("gen_ai.request.model")
                    if model:
                        extra["model"] = model
                    usage = {key: int(handle.attrs[attr]) for key, attr in
                             (("input", "gen_ai.usage.input_tokens"), ("output", "gen_ai.usage.output_tokens"))
                             if attr in handle.attrs}
                    if usage:
                        extra["usage_details"] = usage
                    if "ttft_ms" in handle.attrs:
                        extra["completion_start_time"] = started_at + timedelta(milliseconds=handle.attrs["ttft_ms"])
                obs.update(metadata=handle.attrs, **extra)
        self.collector.add_span(name, duration_ms, **handle.attrs)

    def finish(self, dump: bool = True) -> None:
        # Local trace first: a Langfuse problem (wrong keys, host down) must not hide the result.
        if dump:
            self.collector.dump()
        if self._lf is not None:
            if dump:
                try:
                    print(f"Langfuse trace: {self._lf.get_trace_url(trace_id=self.trace_id)}")
                except Exception as exc:  # noqa: BLE001 - diagnostics only
                    print(f"Langfuse trace URL unavailable ({type(exc).__name__}: {exc}). Check LANGFUSE_* keys and LANGFUSE_HOST.")


def record_feedback(trace_id: str, name: str, value: float) -> None:
    """What a feedback endpoint does when the user clicks thumbs up/down, seconds or minutes later.

    The request (and its trace) finished long ago, so the score is attached by trace ID.
    Your API must return the trace ID to the client for this to work.
    """
    if langfuse_configured():
        _langfuse().create_score(trace_id=trace_id, name=name, value=value)
    print(json.dumps({"feedback": {"trace_id": trace_id, "name": name, "value": value}}))


def flush_traces() -> None:
    """Send what the SDK still buffers. Once per process, before exit: a flush per request blocks on the network."""
    if langfuse_configured():
        _langfuse().flush()


def genai_attributes(input_tokens: int, output_tokens: int) -> dict[str, Any]:
    """OpenTelemetry GenAI attributes for one chat call. operation.name and provider.name are required.

    The simulated calls answer with the requested model; with a real client, take
    gen_ai.response.model from the response (e.g. resp.model), which names the exact snapshot.
    """
    return {
        "gen_ai.operation.name": "chat",
        "gen_ai.provider.name": "openai",
        "gen_ai.request.model": MODEL_NAME,
        "gen_ai.response.model": MODEL_NAME,
        "gen_ai.usage.input_tokens": input_tokens,
        "gen_ai.usage.output_tokens": output_tokens,
    }


# ---------------------------------------------------------------------------
# The agent (this is what you diagnose and fix)
# ---------------------------------------------------------------------------

_TOPICS = [
    "Billing cycles", "Seat management", "Invoices", "Sales tax", "Currencies", "Payment methods",
    None,  # rank 7: the refund policy (EXPECTED_DOC_ID)
    "Data export", "Single sign-on", "Audit logs", "Webhooks", "Rate limits", "Data regions",
    "Backups", "Support hours", "Trials", "Discount codes", "Partner program", "Reseller terms", "Accessibility",
]
# Simulated vector index, in the order its similarity search returns documents for the demo query.
# The answer is NOT the top hit: embeddings rank many near-duplicate "policy" chunks above it.
CORPUS = [
    {"id": "P-101", "text": "[P-101] Refunds: annual plans are eligible for a full refund within 14 days of purchase. "
                            "No refunds after 14 days. Monthly plans can be cancelled at any time; partial months are not refunded."}
    if topic is None else
    {"id": f"D-{300 + i}", "text": f"[D-{300 + i}] {topic}: " + (
        f"This section describes {topic.lower()} for all plans, the related policy details and the settings pages "
        f"where workspace admins can change them. ") * 4}
    for i, topic in enumerate(_TOPICS)
]


def approx_tokens(text: str) -> int:
    """~4 characters per token for English text. In production read the provider's `usage` instead."""
    return max(1, len(text) // 4)


def rewrite_query(query: str) -> tuple[str, int, int]:
    """Small LLM call that turns the user message into a search query."""
    time.sleep(0.08)  # simulated LLM latency
    rewritten = "refund window annual plans"
    return rewritten, approx_tokens("Rewrite as a search query: " + query), approx_tokens(rewritten)


def retrieve_docs(query: str, k: int = 20) -> list[dict]:
    """Vector search: returns the top-k documents in similarity order."""
    time.sleep(0.12)  # simulated vector DB latency
    return CORPUS[:k]


def rerank(query: str, docs: list[dict]) -> list[dict]:
    """Cross-encoder stand-in: scores each candidate against the query and sorts by relevance."""
    time.sleep(0.04)  # simulated reranker latency
    terms = set(re.findall(r"[a-z]+", query.lower()))

    def score(doc: dict) -> int:
        return len(terms & set(re.findall(r"[a-z]+", doc["text"].lower())))

    return sorted(docs, key=score, reverse=True)


def fetch_customer_tier(user_id: str) -> str:
    time.sleep(0.65)  # simulated CRM HTTP call
    return "enterprise"


def fetch_billing_status(user_id: str, request_no: int = 0) -> str:
    time.sleep(0.65)  # simulated Billing HTTP call
    if request_no % 10 == 9:
        time.sleep(1.2)  # every 10th call hits a slow Billing replica: invisible in one trace, obvious in P95
    return "active"


def synthesize_answer(query: str, docs: list[dict], tier: str, status: str) -> tuple[str, int, int, float]:
    context = "\n".join(d["text"] for d in docs)
    input_tokens = approx_tokens(f"System prompt. Customer tier: {tier}, billing: {status}.\n{context}\nQuestion: {query}")
    ttft_ms = 180.0
    time.sleep(0.25)  # simulated time to first token + generation
    if any(d["id"] == EXPECTED_DOC_ID for d in docs):
        answer = f"[{tier}/{status}] Annual plans can be refunded in full within 14 days of purchase [P-101]."
    else:
        answer = f"[{tier}/{status}] I could not find the refund policy in the retrieved documents."
    return answer, input_tokens, approx_tokens(answer), ttft_ms


def run_agent(user_id: str, query: str, request_no: int = 0) -> tuple[str, Tracer]:
    tracer = Tracer(user_id=user_id)

    with tracer.trace("support-rag-agent", input=query, prompt_version=PROMPT_VERSION):
        # Step 1: Query rewrite (small LLM call)
        with tracer.span("query_rewrite", as_type="generation") as span:
            search_query, in_tok, out_tok = rewrite_query(query)
            span.set(**genai_attributes(in_tok, out_tok))

        # Step 2: Retrieval
        with tracer.span("vector_retrieval", as_type="retriever") as span:
            # TODO (Lab 2): Cut the context tokens WITHOUT losing the answer. Try k=4 first and watch
            #   `retrieval_hit` and the answer. Then retrieve 20, `rerank()`, and keep the top 4.
            #   Record retrieval_k (and context_k if you rerank) on the span.
            docs = retrieve_docs(search_query, k=20)
            span.set(doc_count=len(docs), retrieval_hit=any(d["id"] == EXPECTED_DOC_ID for d in docs))

        # Step 3: Tool calls (BOTTLENECK: sequential independent I/O)
        # TODO (Lab 2): Run fetch_customer_tier and fetch_billing_status in parallel (ThreadPoolExecutor)
        #   and keep ONE child span per tool, so the trace still shows which dependency is slow.
        #   OpenTelemetry context lives in contextvars, which do not follow work into threads:
        #   submit each task through its own `contextvars.copy_context().run(...)` and open the span inside it.
        with tracer.span("tool_fetch_customer_tier", as_type="tool"):
            tier = fetch_customer_tier(user_id)

        with tracer.span("tool_fetch_billing_status", as_type="tool"):
            status = fetch_billing_status(user_id, request_no)

        # Step 4: LLM Synthesis
        with tracer.span("llm_synthesis", as_type="generation") as span:
            answer, in_tok, out_tok, ttft_ms = synthesize_answer(query, docs, tier, status)
            span.set(**genai_attributes(in_tok, out_tok), ttft_ms=ttft_ms)
            # TODO (Lab 2): Attach prompt_version and user_tier to this span!

    return answer, tracer


# ---------------------------------------------------------------------------
# Runner: one request (full trace) or many requests (latency percentiles)
# ---------------------------------------------------------------------------


def percentile(values: list[float], q: float) -> float:
    """Nearest-rank percentile: the value below which q% of the observations fall."""
    ordered = sorted(values)
    return ordered[max(0, math.ceil(q / 100 * len(ordered)) - 1)]


def main(
    run: Callable[[str, str, int], tuple[str, Tracer]] = run_agent,
    after_response: Callable[[Tracer], None] | None = None,
) -> None:
    parser = argparse.ArgumentParser(description="Run the agent once (full trace) or N times (P50/P95 per step).")
    parser.add_argument("--requests", type=int, default=1, help="Number of requests; use 10+ to see tail latency")
    args = parser.parse_args()

    durations: dict[str, list[float]] = {}
    for i in range(args.requests):
        answer, tracer = run(f"usr_{42 + i}", DEMO_QUERY, i)
        single = args.requests == 1
        if single:
            print(f"Answer: {answer}\n")
        tracer.finish(dump=single)
        # TODO (Lab 2): The user clicks thumbs-up a few seconds after reading the answer. Attach it to
        #   the trace by ID, the way a feedback endpoint would: record_feedback(tracer.trace_id, "user_thumbs_up", 1.0)
        if after_response is not None:
            after_response(tracer)
        for span in tracer.collector.spans:
            durations.setdefault(span.name, []).append(span.duration_ms)
        durations.setdefault("TOTAL (request)", []).append(tracer.collector.total_ms)
    flush_traces()

    if args.requests > 1:
        print(f"\n{'step':<28}{'P50 ms':>10}{'P95 ms':>10}{'max ms':>10}   (n={args.requests})")
        for name, values in durations.items():
            print(f"{name:<28}{percentile(values, 50):>10.0f}{percentile(values, 95):>10.0f}{max(values):>10.0f}")


if __name__ == "__main__":
    main()
