# Lab 2: Tracing wieloetapowego agenta i diagnoza wąskich gardeł (25 min)

Agent odpowiada na jedno pytanie supportowe w czterech krokach: `query_rewrite` (małe wywołanie LLM) → `vector_retrieval` → dwa wywołania narzędzi (poziom klienta z CRM, status płatności) → `llm_synthesis`.

## Cel
1. **Przeczytaj jeden trace (5 min).** Uruchom agenta raz i przejrzyj spany (w Langfuse albo w lokalnym JSON-ie na stdout). Na co idzie ok. 1,5 s przed wywołaniem syntezy? Który krok generuje tokeny wejściowe?
2. **Spójrz na ogon rozkładu (5 min).** Uruchom `--requests 10` i porównaj P50 i P95 dla każdego kroku. Jedna zależność wygląda dobrze w medianie, a źle w ogonie. Pojedynczy trace tego nie pokaże.
3. **Dodaj instrumentację (5 min).** Dopisz do spanów `prompt_version`, `retrieval_k` i `user_tier`. Podepnij kciuk w górę od użytkownika *po* odpowiedzi, po ID trace'a, tak jak zrobiłby to endpoint feedbacku (`record_feedback`).
4. **Napraw (8 min).**
   - Uruchom oba wywołania narzędzi równolegle, z osobnym spanem potomnym dla każdego narzędzia (zobacz wskazówkę o `contextvars` w TODO).
   - Ogranicz tokeny kontekstu bez gubienia odpowiedzi. Najpierw spróbuj `k=4` i obserwuj `retrieval_hit` oraz odpowiedź. Potem pobierz 20 dokumentów, wywołaj `rerank()` i zostaw 4 najlepsze.
5. **Porównaj (2 min).** P50/P95, tokeny wejściowe i `retrieval_hit` przed zmianami i po nich.

## Uruchomienie

```bash
python lab2_observability/slow_rag_agent.py                 # jedno żądanie: pełny trace jako JSON
python lab2_observability/slow_rag_agent.py --requests 10   # P50 / P95 / max dla każdego kroku (~20 s)
python -m solutions.lab2_fast_rag_agent --requests 10       # rozwiązanie wzorcowe, ten sam format
```

Bez kluczy Langfuse trace jest wypisywany tylko jako JSON. Po ustawieniu `LANGFUSE_PUBLIC_KEY` / `LANGFUSE_SECRET_KEY` / `LANGFUSE_HOST` w `.env` te same spany trafiają do Langfuse (SDK v5, oparte na OpenTelemetry), a skrypt wypisuje URL trace'a.

## Uwagi do omówienia
- **Nie tnij `k` na ślepo.** Odpowiedź jest dopiero na 7. miejscu wyników wyszukiwania wektorowego, więc `k=4` oszczędza tokeny i po cichu ją gubi. Na produkcji mierzy się to przez recall@k na oznaczonym zbiorze zapytań (Część 1.1), a nie na jednym znanym zapytaniu. Pobieraj szeroko, rerankuj, zostawiaj mało.
- **Równoległość nie naprawia ogona.** Po poprawce P50 spada, ale P95 nadal wyznacza wolne wywołanie billingu. Co zrobić: timeout z zapamiętanym statusem, żądanie hedgowane czy rezygnacja z tego wywołania?
- **Feedback przychodzi później.** Gdy użytkownik klika, odpowiedź i jej trace są już zamknięte. API musi zwrócić ID trace'a, żeby klient mógł odesłać z nim ocenę.
- **Trace'y zawierają dane osobowe.** Zapytanie demo zawiera adres e-mail. Tracer maskuje go (`mask_pii`, przekazane do Langfuse jako `mask=`), zanim cokolwiek opuści proces. Dzień 2 (Lab 5) robi to samo z promptami wysyłanymi do modelu.
- **OpenTelemetry a przenośność.** `genai_attributes()` ustawia atrybuty OpenTelemetry GenAI wywołania czatu: wymagane `gen_ai.operation.name` i `gen_ai.provider.name`, model z żądania i z odpowiedzi oraz zużycie tokenów. `Tracer.span` sam przepisuje model i zużycie do własnych pól Langfuse; to kod tego skryptu, a nie coś, co każdy backend zrobi za Ciebie. Lab korzysta z SDK Langfuse. Żeby móc zmienić backend, instrumentuj czystym SDK OpenTelemetry i eksportuj przez OTLP (Langfuse też przyjmuje OTLP). Konwencje GenAI mają wciąż status Development i ciągle się zmieniają (np. `gen_ai.usage.prompt_tokens` zmieniło się w `gen_ai.usage.input_tokens`, a `gen_ai.system` w `gen_ai.provider.name`), więc przypnij wersję konwencji, którą emitujesz.
- Liczby tokenów są tu szacowane (~4 znaki na token). Na produkcji odczytuj `usage` z odpowiedzi dostawcy.
