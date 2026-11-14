# Lab 3: Bramka regresji w CI/CD (`promptfoo` + `pytest`) (30 min)

## Cel
1. Porównaj `prompt_baseline.txt` z `prompt_candidate_regressed.txt`. Zauważ, że kandydat poprawia uprzejmość, ale **usuwa wymóg cytowania** (cicha regresja!).
2. Uruchom bramkę CI w `pytest`, aby sprawdzić, że progi deterministyczne + faithfulness wychwytują regresję.
3. Opcjonalnie uruchom `promptfoo eval`, aby zobaczyć porównanie obok siebie w macierzy HTML.
4. Popraw `prompt_candidate_regressed.txt` tak, aby przechodził wszystkie bramki CI.

Oba pliki promptów to kompletne szablony z placeholderami `{{context}}` i `{{query}}`. `pytest` i `promptfoo` wypełniają je w ten sam sposób i czytają ten sam plik `golden_dataset.jsonl` (format przypadków testowych promptfoo: `{"description": ..., "vars": {...}}`).

## Uruchomienie

```bash
# Bramka CI w pytest (domyślnie symulacja offline; ustaw LIVE_EVAL=1, aby wywołać prawdziwy model)
pytest lab3_ci_gate/test_ci_gate.py -v
LIVE_EVAL=1 pytest lab3_ci_gate/test_ci_gate.py -v

# Opcjonalnie: porównanie obok siebie w Promptfoo (wymaga OPENAI_API_KEY w ../.env)
cd lab3_ci_gate
promptfoo eval --env-file ../.env
promptfoo view
```

`promptfoo eval` kończy się kodem 100, gdy którykolwiek test nie przejdzie. Przy zregresowanym kandydacie jest to oczekiwane, więc uruchom `promptfoo view` jako osobne polecenie, a nie po `&&`. W CI to właśnie ten niezerowy kod wyjścia blokuje merge.

Test `test_candidate_passes_ci_gate` powinien kończyć się FAIL, dopóki nie poprawisz promptu kandydata.
