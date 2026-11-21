# Lab 2: Tracing a Multi-Step Agent & Bottleneck Diagnosis (25 min)

The agent answers one support question in four steps: `query_rewrite` (small LLM call) → `vector_retrieval` → two tool calls (CRM tier, billing status) → `llm_synthesis`.

## Goal
1. **Read one trace (5 min).** Run the agent once and inspect the spans (Langfuse or the local JSON on stdout). Where do the ~1.5 s before the synthesis call go? Which step drives the input tokens?
2. **Look at the tail (5 min).** Run `--requests 10` and compare P50 and P95 per step. One dependency is fine in the median and slow in the tail. A single trace cannot show you that.
3. **Instrument (5 min).** Add `prompt_version`, `retrieval_k` and `user_tier` to the spans. Attach the user's thumbs-up *after* the response, by trace ID, like a feedback endpoint would (`record_feedback`).
4. **Fix (8 min).**
   - Run the two tool calls in parallel, with one child span per tool (see the hint in the TODO about `contextvars`).
   - Cut the context tokens without losing the answer. Try `k=4` first and watch `retrieval_hit` and the answer. Then retrieve 20, `rerank()`, and keep the top 4.
5. **Compare (2 min).** P50/P95, input tokens and `retrieval_hit`, before and after.

## Run

```bash
python lab2_observability/slow_rag_agent.py                 # one request: full trace as JSON
python lab2_observability/slow_rag_agent.py --requests 10   # P50 / P95 / max per step (~20 s)
python -m solutions.lab2_fast_rag_agent --requests 10       # reference solution, same output
```

Without Langfuse keys the trace is printed as JSON only. With `LANGFUSE_PUBLIC_KEY` / `LANGFUSE_SECRET_KEY` / `LANGFUSE_HOST` set in `.env`, the same spans are sent to Langfuse (SDK v5, OpenTelemetry-based) and the script prints the trace URL.

## Notes for the debrief
- **Do not cut `k` blind.** The answer ranks 7th in the vector search, so `k=4` saves tokens and silently loses it. In production you measure that with recall@k on a labeled query set (Unit 1.1), not with one known query. Retrieve wide, rerank, keep few.
- **Parallel is not enough for the tail.** After the fix, P50 drops but P95 is still set by the slow billing call. What would you do: a timeout with a cached status, a hedged request, or dropping the call?
- **Feedback arrives later.** The response, and its trace, are finished by the time the user clicks. The API must return the trace ID so the client can send the score with it.
- **Traces carry personal data.** The demo query contains an e-mail address. The tracer masks it (`mask_pii`, passed to Langfuse as `mask=`) before anything leaves the process. Day 2 (Lab 5) does the same for prompts sent to the model.
- **OpenTelemetry and portability.** `Tracer.span` copies the OpenTelemetry GenAI attributes (`gen_ai.request.model`, `gen_ai.usage.input_tokens` / `output_tokens`) into Langfuse's model and usage fields itself; that is plumbing in this script, not something every backend does for you. This lab uses the Langfuse SDK. To be able to switch backends, instrument with the plain OpenTelemetry SDK and export over OTLP (Langfuse accepts OTLP too). The GenAI conventions are still changing (e.g. `gen_ai.usage.prompt_tokens` became `gen_ai.usage.input_tokens`), so pin the convention version you emit.
- Token counts here are estimated (~4 characters per token). In production, read the provider's `usage`.
