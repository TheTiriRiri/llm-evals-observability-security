# Lab 2: Tracing wieloetapowego agenta i diagnoza wąskich gardeł (25 min)

## Cel
1. Uruchom `slow_rag_agent.py` i przeanalizuj wygenerowane spany trace'a (w **Langfuse** albo w lokalnym trace'ie JSON wypisanym na stdout).
2. Zidentyfikuj **dwa podrzucone wąskie gardła**:
   - Dlaczego żądanie spędza ok. 1,4 s, zanim w ogóle zostanie wywołany LLM?
   - Który etap generuje koszt tokenów wejściowych i jaką jego część da się uniknąć?
3. Dodaj brakujące metadane spanów (`prompt_version`, `retrieval_k`, `user_tier`) i dołącz do trace'a ocenę użytkownika (`user_thumbs_up = 1.0`).
4. Usuń wąskie gardła (zrównoleglij niezależne wywołania narzędzi + zmniejsz `k` / przytnij kontekst) i porównaj metryki trace'a przed i po zmianach.

## Uruchomienie

```bash
python lab2_observability/slow_rag_agent.py
```

Bez kluczy Langfuse trace jest wypisywany tylko jako JSON. Po ustawieniu `LANGFUSE_PUBLIC_KEY` / `LANGFUSE_SECRET_KEY` / `LANGFUSE_HOST` w `.env` te same spany są wysyłane do Langfuse (SDK v5, oparte na OpenTelemetry), a skrypt wypisuje URL trace'a.

Span `llm_synthesis` używa nazw atrybutów OpenTelemetry GenAI (`gen_ai.request.model`, `gen_ai.usage.input_tokens`); Langfuse mapuje je na model i zużycie tokenów.
