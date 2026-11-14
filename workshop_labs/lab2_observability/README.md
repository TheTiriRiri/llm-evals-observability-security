# Lab 2: Tracing a Multi-Step Agent & Bottleneck Diagnosis (25 min)

## Goal
1. Run `slow_rag_agent.py` and inspect the emitted trace spans (either in **Langfuse** or the local JSON trace printed to stdout).
2. Identify the **two planted bottlenecks**:
   - Why does the request spend ~1.4s before the LLM is even called?
   - Which step drives the input token cost, and how much of it is avoidable?
3. Add missing span metadata (`prompt_version`, `retrieval_k`, `user_tier`) and attach a user feedback score (`user_thumbs_up = 1.0`) to the trace.
4. Fix the bottlenecks (parallelize independent tool calls + reduce `k` / trim context) and compare before/after trace metrics.

## Run

```bash
python lab2_observability/slow_rag_agent.py
```

Without Langfuse keys the trace is printed as JSON only. With `LANGFUSE_PUBLIC_KEY` / `LANGFUSE_SECRET_KEY` / `LANGFUSE_HOST` set in `.env`, the same spans are sent to Langfuse (SDK v5, OpenTelemetry-based) and the script prints the trace URL.

The `llm_synthesis` span uses OpenTelemetry GenAI attribute names (`gen_ai.request.model`, `gen_ai.usage.input_tokens`); Langfuse maps them to model and token usage.
