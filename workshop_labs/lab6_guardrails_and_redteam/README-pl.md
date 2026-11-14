# Lab 6: Guardrails w czasie działania i automatyczny red teaming (30 min)

## Cel
1. Zaimplementuj warstwowe guardrails w czasie działania w `guardrails.py`:
   - **Guardrail wejściowy:** Szybki, deterministyczny + heurystyczny detektor injection.
   - **Guardrail wykonania narzędzi:** Bramka człowieka w pętli (HITL) / polityk dla wywołań narzędzi modyfikujących stan (`delete_workspace`, `send_external_email`).
   - **Guardrail wyjściowy:** Sprawdzenie wycieku PII/sekretów przed zwróceniem odpowiedzi użytkownikowi.
2. Uruchom `pytest lab6_guardrails_and_redteam/test_redteam_regressions.py -v`, aby sprawdzić, czy twoje guardrails blokują znane exploity.
3. Opcjonalnie uruchom skan red teamingowy promptfoo (lub `garak`), aby poszukać dodatkowych podatności, i zamień 2 wykryte błędy w stałe przypadki regresyjne w `pytest`.

## Uruchomienie

```bash
pytest lab6_guardrails_and_redteam/test_redteam_regressions.py -v

# Opcjonalny skan red teamingowy (wymaga OPENAI_API_KEY; uruchamiaj w aktywowanym .venv)
cd lab6_guardrails_and_redteam
PROMPTFOO_DISABLE_REDTEAM_REMOTE_GENERATION=true promptfoo redteam run -c promptfooconfig_redteam.yaml --env-file ../.env
promptfoo redteam report
```

Celem skanu jest `redteam_target.py`: każdy atak przechodzi przez `check_input_guardrail`, następnie przez LLM (z narzędziami), potem przez `check_tool_policy` dla każdego wywołania narzędzia, a na końcu przez `check_output_guardrail`. Zmiany wprowadzone w `guardrails.py` są widoczne przy następnym skanie. promptfoo uruchamia target za pomocą `python` dostępnego w twoim `PATH` (można to nadpisać przez `PROMPTFOO_PYTHON=/sciezka/do/python`).

### Generowanie ataków: lokalnie vs. przez usługę promptfoo

- **Lokalnie (polecenie powyżej, zalecane na warsztatach):** `PROMPTFOO_DISABLE_REDTEAM_REMOTE_GENERATION=true` sprawia, że promptfoo generuje i ocenia ataki z użyciem twojego własnego `OPENAI_API_KEY`. Konto w promptfoo nie jest potrzebne. Konfiguracja używa wyłącznie pluginów i strategii obsługujących ten tryb.
- **Usługa generowania promptfoo:** usuń tę zmienną. Przy pierwszym uruchomieniu promptfoo poprosi o adres e-mail i go zweryfikuje (jednorazowo, interaktywnie), więc zrób to przed warsztatami, a nie w trakcie labu. Ten tryb odblokowuje dodatki dostępne tylko zdalnie, takie jak plugin `hijacking` i strategia `jailbreak:meta`.

### Co sprawdza skan

Target przekazuje modelowi prawdziwe definicje narzędzi i przepuszcza każde wywołanie narzędzia przez `check_tool_policy`, zanim cokolwiek zostanie wykonane (narzędzia są symulowane). Dwa przełączniki:

- `REDTEAM_HITL_APPROVED=1` symuluje człowieka, który zatwierdza każde żądanie (zmęczenie zatwierdzaniem, approval fatigue). HITL przestaje wtedy pomagać, więc allowlista domen e-mail (twoje TODO w `check_tool_policy`) staje się ostatnią linią obrony.
- `GUARDRAILS_IMPL=solution` skanuje rozwiązanie referencyjne zamiast twojego `guardrails.py` — przydatne do porównania przed/po.
