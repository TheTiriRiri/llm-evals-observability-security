# Lab 1: Analiza błędów i skalibrowany LLM-as-a-Judge (35 min)

## Dane
`traces_sample.jsonl` zawiera 40 trace'ów z bota supportowego RAG: 20 `dev` i 20 `val`. Każdy trace ma zapytanie, pobrane dokumenty (oznaczone `[ID]`), surową odpowiedź modelu oraz osobną etykietę ludzką dla każdego trybu awarii:

| Pole | Znaczenie |
| :--- | :--- |
| `labels.format` | Poprawny JSON z polami `answer` i `citations` |
| `labels.citation` | Są cytowania (chyba że odpowiedź mówi, że dokumentacja nie obejmuje pytania) i każde cytowane ID występuje w pobranym kontekście |
| `labels.faithfulness` | Każde twierdzenie ma oparcie w pobranym kontekście; odpowiedź „dokumentacja tego nie obejmuje” liczy się jako wierna |
| `human_label` | Werdykt ogólny: FAIL, jeśli którakolwiek z powyższych etykiet to FAIL |

`null` oznacza „nie dotyczy”: odpowiedź, która nie jest JSON-em, nie dostaje etykiety cytowań ani wierności.

## Cel
1. **Analiza błędów (10 min).** Przeczytaj 20 trace'ów `dev`, nie zaglądając do `labels` ani `failure_note`. Przy każdym złym trace'ie zapisz krótką notatkę (open coding), pogrupuj notatki w tryby awarii (axial coding) i uszereguj je według częstość × waga. Dopiero potem porównaj z `failure_note`.
2. **Testy deterministyczne (3 min).** `check_format` i `check_citations` są już zaimplementowane. Przeczytaj je: które z Twoich trybów awarii wyłapują, a które może wyłapać tylko ewaluator semantyczny?
3. **Sędzia bazowy (5 min).** Uruchom ogólnikową rubrykę 1–5 (`--judge likert`) i przeczytaj, gdzie nie zgadza się z ludźmi. Szukaj dwóch wzorców: poprawne odpowiedzi „dokumentacja tego nie obejmuje” ocenione jako złe oraz płynne, pewne siebie zmyślenia ocenione jako dobre.
4. **Sędzia binarny (12 min).** Przepisz `JUDGE_SYSTEM_PROMPT` (binarny PASS/FAIL, uzasadnienie przed werdyktem) pod tryby awarii z kroku 1. Iteruj wyłącznie na `dev`.
5. **Ocena na zbiorze wydzielonym (5 min).** Zamroź prompt i uruchom raz `--split val`. Podaj precision i recall sędziego wraz z przedziałami; cel to ≥ 0,85 dla obu jako estymacja punktowa.

## Uruchomienie

```bash
# Offline: testy deterministyczne + prymitywny numeryczny zamiennik sędziego (bez kosztów API)
python lab1_evals_and_judge/judge_starter.py --mock

# Na żywo (OPENAI_API_KEY z .env): najpierw rubryka 1-5, potem Twój sędzia binarny, oba na dev
python lab1_evals_and_judge/judge_starter.py --judge likert
python lab1_evals_and_judge/judge_starter.py

# Końcowy raport na wydzielonym zbiorze, gdy prompt jest już zamrożony
python lab1_evals_and_judge/judge_starter.py --split val

# Prompt wzorcowy, do porównania po napisaniu własnego
python lab1_evals_and_judge/judge_starter.py --judge-prompt solutions/lab1_judge_prompt.txt
```

## Jak czytać raport
- Każdy ewaluator jest oceniany tylko względem etykiety własnego trybu awarii. Gdyby sędziego wierności porównywać z `human_label`, dostawałby punkty za błędy JSON-a i cytowań, których w ogóle nie sprawdza: `t07` to wierna odpowiedź, która pada wyłącznie przez brak cytowania.
- Klasa pozytywna to FAIL, czyli wyłapana awaria. Precision: jak często FAIL od ewaluatora to prawdziwa awaria. Recall: ile prawdziwych awarii wyłapuje. Kappa: zgodność skorygowana o przypadek.
- `val` ma 8 awarii wierności. Jedna pomyłka zmienia recall o 12,5 punktu, a 95-procentowy przedział ma rozpiętość kilkudziesięciu punktów. Czytaj niezgodności, nie tylko wyniki. Sędzia, któremu można zaufać w CI, potrzebuje kilkuset etykiet, a etykietujący ludzie powinni najpierw zgadzać się między sobą (kappa między anotatorami), zanim porównasz z nimi sędziego.
- Nie dostrajaj promptu sędziego na `val`, bo jego ocena przestanie być uczciwa.
- `--mock` zastępuje sędziego heurystyką, która oznacza liczby nieobecne w kontekście. Celowo pomija awarie nienumeryczne, więc wyniki w trybie mock nie są celem.
