# Lab 1: Analiza błędów i skalibrowany LLM-as-a-Judge (35 min)

## Cel
1. Przeprowadź **open i axial coding** na pierwszych 20 trace'ach w `traces_sample.jsonl` (`split == "dev"`), aby zidentyfikować 3 główne tryby awarii.
2. Zaimplementuj **deterministyczny test w kodzie** dla błędów strukturalnych/ograniczeń (np. niepoprawny JSON lub brak wymaganego formatu cytowania).
3. Zaimplementuj **binarnego sędziego LLM-as-a-Judge** (`PASS` / `FAIL`) oceniającego **ugruntowanie w źródłach (Groundedness / Faithfulness)**, który zwraca uzasadnienie *przed* werdyktem.
4. Skalibruj sędziego względem `human_label` na pozostałych 20 trace'ach (`split == "val"`), celując w **Precision >= 0.85** i **Recall >= 0.85**.

## Uruchomienie

```bash
# Tryb offline/mock (testuje deterministyczne sprawdzenia i pipeline bez kosztów API)
python lab1_evals_and_judge/judge_starter.py --mock

# Tryb na żywo (używa OPENAI_API_KEY z .env); iteruj nad promptem sędziego na zbiorze dev
python lab1_evals_and_judge/judge_starter.py --split dev

# Końcowy raport na wydzielonym zbiorze, gdy prompt jest już zamrożony
python lab1_evals_and_judge/judge_starter.py --split val
```

Domyślna wartość `--split` to `dev`. Nie dostrajaj promptu sędziego na zbiorze `val`, bo wtedy precision/recall przestaną być uczciwym oszacowaniem.

Sędzia w trybie `--mock` to prymitywny zamiennik, który oznacza jedynie liczby nieobecne w kontekście. Celowo pomija sprzeczności nienumeryczne, więc precision/recall w trybie mock nie jest wynikiem, do którego należy dążyć.
