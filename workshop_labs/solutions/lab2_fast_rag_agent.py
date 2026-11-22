"""Lab 2 Solution: rerank instead of a blind k cut, parallel tools with one span each, full metadata, async feedback."""

from __future__ import annotations

import contextvars
from concurrent.futures import ThreadPoolExecutor

from dotenv import load_dotenv

from lab2_observability.slow_rag_agent import (
    EXPECTED_DOC_ID,
    PROMPT_VERSION,
    Tracer,
    fetch_billing_status,
    fetch_customer_tier,
    genai_attributes,
    main,
    record_feedback,
    rerank,
    retrieve_docs,
    rewrite_query,
    synthesize_answer,
)

load_dotenv()

RETRIEVAL_K = 20  # candidates from the vector index: keep recall high
CONTEXT_K = 4     # documents that reach the prompt after reranking: keep tokens low


def run_fast_agent(user_id: str, query: str, request_no: int = 0) -> tuple[str, Tracer]:
    tracer = Tracer(user_id=user_id)

    def traced_tool(name: str, fn, *args):
        # Runs inside a copied context, so this span's parent is the root observation of this request.
        with tracer.span(name, as_type="tool"):
            return fn(*args)

    with tracer.trace("support-rag-agent", input=query, prompt_version=PROMPT_VERSION):
        with tracer.span("query_rewrite", as_type="generation") as span:
            search_query, in_tok, out_tok = rewrite_query(query)
            span.set(**genai_attributes(in_tok, out_tok), prompt_version=PROMPT_VERSION)

        # Cutting k to 4 at the vector index drops the answer (it ranks 7th). Retrieve wide, rerank, keep few.
        with tracer.span("vector_retrieval", as_type="retriever", retrieval_k=RETRIEVAL_K) as span:
            candidates = retrieve_docs(search_query, k=RETRIEVAL_K)
            # Two questions, two attributes: is the answer among the 20 candidates, and does it survive the cut?
            span.set(doc_count=len(candidates), retrieval_hit=any(d["id"] == EXPECTED_DOC_ID for d in candidates))
        with tracer.span("rerank", context_k=CONTEXT_K) as span:
            docs = rerank(search_query, candidates)[:CONTEXT_K]
            span.set(kept_doc_ids=[d["id"] for d in docs], retrieval_hit=any(d["id"] == EXPECTED_DOC_ID for d in docs))

        # Independent CRM and Billing calls in parallel (~650 ms instead of ~1300 ms), one child span per tool.
        # Each task gets its own copy of the current context: a Context cannot be entered by two threads at once.
        with ThreadPoolExecutor(max_workers=2) as pool:
            tier_fut = pool.submit(contextvars.copy_context().run, traced_tool,
                                   "tool_fetch_customer_tier", fetch_customer_tier, user_id)
            status_fut = pool.submit(contextvars.copy_context().run, traced_tool,
                                     "tool_fetch_billing_status", fetch_billing_status, user_id, request_no)
            tier, status = tier_fut.result(), status_fut.result()

        with tracer.span("llm_synthesis", as_type="generation") as span:
            answer, in_tok, out_tok, ttft_ms = synthesize_answer(query, docs, tier, status)
            span.set(
                **genai_attributes(in_tok, out_tok),
                ttft_ms=ttft_ms,
                prompt_version=PROMPT_VERSION,
                user_tier=tier,
            )

    return answer, tracer


def send_thumbs_up(tracer: Tracer) -> None:
    # Arrives after the response, from the client, carrying the trace ID the API returned.
    record_feedback(tracer.trace_id, "user_thumbs_up", 1.0)


if __name__ == "__main__":
    # Same runner as the starter: `--requests 10` prints P50/P95 per step.
    main(run=run_fast_agent, after_response=send_thumbs_up)
