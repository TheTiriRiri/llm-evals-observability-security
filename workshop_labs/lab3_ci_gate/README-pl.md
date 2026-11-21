# Lab 3: Bramka regresji w CI/CD (`promptfoo` + `pytest`) (30 min)

Kolega otwiera PR, który „tylko sprawia, że asystent jest milszy”. Format JSON i cytowania zostają bez zmian. Twoja bramka musi zdecydować, czy można go zmergować.

## Cel
1. **Przeczytaj PR (5 min).** Porównaj `prompt_baseline.txt` z `prompt_candidate_regressed.txt`. Co oprócz tonu zmieniło się w zachowaniu? Przewidź, które wiersze `golden_dataset.jsonl` się zregresują.
2. **Uruchom bramkę (5 min).** Poprawność schematu wynosi 100%, a ogólny odsetek zaliczeń przekracza próg 90%, a mimo to bramka nie przechodzi. Przeczytaj tabelę per slice i listę przypadków, które zmieniły się z PASS na FAIL.
3. **Omów (5 min).** Dlaczego próg łączny to przepuszcza? Co mówią przedziały ufności dla slice'a z 2 wierszami? Ile wierszy chcesz mieć w każdym krytycznym slice'ie?
4. **Popraw kandydata (10 min).** Zachowaj milszy ton i przywróć regułę odmowy odpowiedzi. Offline edytowany prompt nie ma nagranych odpowiedzi, więc bramka blokuje go domyślnie: oceń swoją wersję z `LIVE_EVAL=1` albo porównaj z poprawką wzorcową (`PROMPT_CANDIDATE`, niżej).
5. **Opcjonalnie (5 min).** Puść ten sam zbiór przez `promptfoo`, żeby zobaczyć macierz HTML obok siebie, oraz sędziego wierności z Lab 1 na żywo.

## Uruchomienie

```bash
# Offline: odtwarza odpowiedzi nagrane w fixtures/ dla wersji promptów dołączonych do labu
pytest lab3_ci_gate -v --tb=short

# Offline, poprawka wzorcowa zamiast zregresowanego kandydata
PROMPT_CANDIDATE=../solutions/lab3_prompt_candidate_fixed.txt pytest lab3_ci_gate -v --tb=short

# Model na żywo; uruchamia też sędziego wierności z Lab 1 (Twój prompt albo wzorcowy)
LIVE_EVAL=1 pytest lab3_ci_gate -v --tb=short
LIVE_EVAL=1 JUDGE_PROMPT_FILE=solutions/lab1_judge_prompt.txt pytest lab3_ci_gate -v --tb=short

# Ponowne nagranie fixtures z prawdziwego modelu
LIVE_EVAL=1 RECORD_FIXTURES=1 pytest lab3_ci_gate

# Opcjonalnie: porównanie obok siebie w promptfoo (wymaga OPENAI_API_KEY w ../.env)
cd lab3_ci_gate
promptfoo eval --env-file ../.env
promptfoo view
```

Test `test_candidate_no_slice_regression` powinien kończyć się FAIL, dopóki nie poprawisz kandydata. Test wierności na żywo jest pomijany bez `LIVE_EVAL=1`.

## Jak działa bramka
- **Zbiór.** `golden_dataset.jsonl` ma 20 wierszy w formacie przypadków testowych promptfoo: 18 `answerable` (musi pojawić się oczekiwany fakt i cytowanie) i 2 `not_covered` (kontekst nie odpowiada na pytanie; asystent ma to powiedzieć zamiast zgadywać). `pytest` i `promptfoo` czytają ten sam plik i tak samo wypełniają prompty.
- **Reguły.** Poprawność schematu 100%; ogólny odsetek zaliczeń ≥ 90%; a w porównaniu parowanym na tych samych wejściach żaden slice nie może spaść o więcej niż 5 punktów poniżej baseline'u. Testy deterministyczne działają zawsze; semantyczna wierność wymaga sędziego na żywo.
- **Fixtures.** Offline bramka odtwarza `fixtures/<prompt>.json`, dopasowane po SHA-256 pliku promptu. Dołączone fixtures to ręcznie napisane przykłady typowych odpowiedzi modelu na każdy prompt, żeby lab działał bez klucza API; nie są nagraniami. `RECORD_FIXTURES=1` zastępuje je prawdziwymi odpowiedziami. Prompt bez pasującego fixture'a nie przechodzi: bramka nigdy nie może przepuścić promptu, którego nikt nie ocenił.
- **Małe slice'y.** 0/2 wobec 2/2 wystarcza, żeby zablokować merge, ale slice z 2 wierszami ma 95-procentowy przedział 34–100% nawet wtedy, gdy wszystko przechodzi. W prawdziwej bramce daj każdemu krytycznemu slice'owi (odmowa odpowiedzi, bezpieczeństwo, intencje o dużej wartości) tyle wierszy, żeby wynik coś znaczył, a pełny zbiór uruchamiaj co noc.
- **Grader promptfoo** (`llm-rubric`) to nieskalibrowany sędzia LLM. Traktuj jego FAIL-e jako tropy; bramka w pytest używa sędziego skalibrowanego w Lab 1.
- `promptfoo eval` kończy się kodem 100, gdy którykolwiek test nie przejdzie. Przy zregresowanym kandydacie jest to oczekiwane, więc uruchom `promptfoo view` jako osobne polecenie, a nie po `&&`. W CI to właśnie ten niezerowy kod wyjścia blokuje merge.
