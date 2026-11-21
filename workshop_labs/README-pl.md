# Produkcyjna inżynieria AI — laboratoria warsztatowe

Wszystkie laby są napisane w **Pythonie 3.11+** i można je uruchamiać na żywym API modelu LLM (`OPENAI_API_KEY`) albo — tam, gdzie zaznaczono — w **trybie offline/mock**, dzięki czemu uczestnicy mogą szybko iterować bez uderzania w limity zapytań.

## Wymagania i konfiguracja

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
cp .env.example .env
python -m spacy download en_core_web_sm   # Lab 5 (NER dla Presidio, ~12 MB)
python check_env.py                       # kończy się kodem 1, jeśli brakuje czegoś wymaganego
```

`OPENAI_API_KEY` jest potrzebny tylko w wariantach na żywo (prawdziwy sędzia w Labie 1, `LIVE_EVAL=1` w Labie 3, skan red teamingowy w Labie 6; testy regresyjne z Labu 6 działają offline). Red teaming w Labie 6 działa w trybie lokalnego generowania, więc nie wymaga konta w promptfoo (szczegóły w README Labu 6). Klucze Langfuse są opcjonalne: bez nich Lab 2 wypisuje trace lokalnie. Uruchom `check_env.py` kilka dni przed warsztatami, a nie rano w dniu warsztatów.

Do **Labu 3** i **Labu 6** zainstaluj Promptfoo (wymagany Node.js 18+):
```bash
npm install -g promptfoo
```

Do **Labu 6** (opcjonalne: szerokie sondowanie samego modelu, a nie twoich guardrails):
```bash
pip install garak
```

## Spis labów

| Lab | Dzień | Temat | Katalog |
| :--- | :--- | :--- | :--- |
| **Lab 1** | Dzień 1 | Analiza błędów i skalibrowany LLM-as-a-Judge | [lab1_evals_and_judge/README-pl.md](./lab1_evals_and_judge/README-pl.md) |
| **Lab 2** | Dzień 1 | Tracing wieloetapowego agenta i diagnoza wąskich gardeł | [lab2_observability/README-pl.md](./lab2_observability/README-pl.md) |
| **Lab 3** | Dzień 1 | Bramka regresji w CI/CD (`promptfoo` + `pytest`) | [lab3_ci_gate/README-pl.md](./lab3_ci_gate/README-pl.md) |
| **Lab 4** | Dzień 2 | Modelowanie zagrożeń agentowej aplikacji RAG | [lab4_threat_modeling/README-pl.md](./lab4_threat_modeling/README-pl.md) |
| **Lab 5** | Dzień 2 | Łamanie i utwardzanie podatnego asystenta | [lab5_attack_and_harden/README-pl.md](./lab5_attack_and_harden/README-pl.md) |
| **Lab 6** | Dzień 2 | Guardrails w czasie działania i automatyczny red teaming | [lab6_guardrails_and_redteam/README-pl.md](./lab6_guardrails_and_redteam/README-pl.md) |
