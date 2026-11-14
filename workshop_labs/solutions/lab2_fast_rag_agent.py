"""Lab 2 Solution: Parallelized I/O, tuned retrieval k, full span metadata & feedback score."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor

from dotenv import load_dotenv

from lab2_observability.slow_rag_agent import (
    MODEL_NAME,
    PROMPT_VERSION,
    Tracer,
    fetch_billing_status,
    fetch_customer_tier,
    retrieve_docs,
    synthesize_answer,
)

load_dotenv()


def run_fast_agent(user_id: str, query: str) -> None:
    tracer = Tracer(user_id=user_id)
    retrieval_k = 4  # Reduced from 20 -> 80% fewer context tokens

    with tracer.trace("support-rag-agent", prompt_version=PROMPT_VERSION):
        with tracer.span("vector_retrieval", as_type="retriever", retrieval_k=retrieval_k) as span:
            docs = retrieve_docs(query, k=retrieval_k)
            span.set(doc_count=len(docs))

        # Parallelize independent CRM & Billing tool calls (~650ms instead of ~1300ms).
        # The span lives in the main thread; worker threads only run plain I/O functions.
        with tracer.span("parallel_customer_context", as_type="tool") as span:
            with ThreadPoolExecutor(max_workers=2) as pool:
                tier_fut = pool.submit(fetch_customer_tier, user_id)
                status_fut = pool.submit(fetch_billing_status, user_id)
                tier = tier_fut.result()
                status = status_fut.result()
            span.set(user_tier=tier)

        with tracer.span("llm_synthesis", as_type="generation") as span:
            answer, input_tokens = synthesize_answer(query, docs, tier, status)
            span.set(
                **{"gen_ai.request.model": MODEL_NAME, "gen_ai.usage.input_tokens": input_tokens},
                prompt_version=PROMPT_VERSION,
                user_tier=tier,
            )

        tracer.score("user_thumbs_up", 1.0)

    print(f"Answer: {answer}\n")
    tracer.finish()


if __name__ == "__main__":
    run_fast_agent(user_id="usr_42", query="What is the refund window?")
