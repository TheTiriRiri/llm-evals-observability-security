# Dodatek do samodzielnej nauki: co nie zmieściło się w siedmiu godzinach

**Stan na:** listopad 2026. Fakty sprawdzono w źródłach wymienionych na końcu. Tam, gdzie były dostępne tylko źródła wtórne albo źródła sobie przeczą, tekst mówi **(do weryfikacji)**: sprawdź tekst źródłowy, zanim się na nim oprzesz. Nic tutaj nie jest poradą prawną.

Każda sekcja mówi, dlaczego temat jest ważny i co z nim zrobić. Sekcja 9 zawiera ćwiczenia rozszerzające laby.

---

## 1. Ewaluacja agentów, a nie tylko odpowiedzi

Laby 1 i 3 oceniają pojedyncze odpowiedzi. Agent psuje się inaczej: wybiera złe narzędzie, przekazuje złe argumenty, pomija potwierdzenie albo kończy w złym stanie, choć każda pojedyncza wiadomość wygląda dobrze.

- **Oceniaj trajektorię i stan końcowy.**
  - *Trajektoria:* które narzędzia, z jakimi argumentami, w jakiej kolejności i czego odmówiono.
  - *Stan końcowy:* porównaj stan systemu po rozmowie z oczekiwanym. τ-bench ocenia agentów, porównując stan bazy danych na końcu rozmowy ze stanem docelowym przygotowanym przez anotatorów [1].
- **Mierz spójność przez pass^k.** pass^k liczy zadanie jako rozwiązane tylko wtedy, gdy udaje się we wszystkich k niezależnych próbach [1].
  - W pracy o τ-bench nawet gpt-4o rozwiązał mniej niż 50% zadań, a jego pass^8 w domenie retail wyniósł poniżej 25%.
  - Opieraj bramkę na pass^k, a nie na pass@k: pass@k liczy zadanie jako rozwiązane, jeśli zadziała którakolwiek z k prób, więc nagradza agenta, który działa tylko czasami.
  - Autorzy wskazują teraz τ²-bench jako utrzymywanego następcę [2].
- **Symulowani użytkownicy to też LLM-y.** Ewaluacje wieloturowe potrzebują symulatora użytkownika. Może on dryfować i zdradzać cel, więc czytaj jego transkrypcje i kalibruj go jak każdego innego sędziego.
- **Przepis:**
  1. Zrób analizę błędów na trace'ach agenta (drzewo spanów z Labu 2). Oznacz błędy na poziomie narzędzi: złe narzędzie, złe argumenty, brak potwierdzenia, zbędne wywołanie.
  2. Najpierw napisz deterministyczne sprawdzenia: nazwy narzędzi i schematy argumentów, zakazane narzędzia, asercje na stanie końcowym.
  3. Sędziego LLM dodaj tylko do tego, czego kod nie sprawdzi, np. czy odmowa była uzasadniona.
  4. Uruchom każdy przypadek k razy i raportuj pass^k z przedziałem.
- **Rozszerz Lab 6:** jego testy odtwarzające (replay) już sprawdzają trajektorię (`run.executed`) z oskryptowanym modelem. Uruchom te same asercje k razy na żywym modelu i masz ewaluację agenta.

---

## 2. Projektowanie agentów odpornych na prompt injection

Dzień 2 pokazuje, że wykrywanie to sygnał, a nie granica bezpieczeństwa.
- W pracy „The Attacker Moves Second” adaptacyjne ataki złamały 12 opublikowanych obron, przeważnie ze skutecznością powyżej 90% [3].
- Spotlighting obniżył skuteczność ataków z ponad 50% do poniżej 2% dla statycznych ataków z pracy, która go opisuje [4]. To przydatne ograniczenie, a nie gwarancja.
- Klasyfikatory to też sygnał. Llama Prompt Guard 2 [23] ma wielojęzyczny model 86M i model 22M nastawiony na angielski, a polskiego nie ma wśród języków, na których go oceniano. Zmierz każdy klasyfikator na własnym ruchu, zanim się na nim oprzesz.
- Pozostaje architektura: spraw, żeby wstrzyknięty tekst nie mógł wyrządzić szkody, nawet gdy model go posłucha.

**Sześć wzorców projektowych** [5]. Wspólna zasada: gdy agent przyjął niezaufane wejście, to wejście nie może wywołać skutków ubocznych.

| Wzorzec | Idea |
| :--- | :--- |
| Action-Selector | Model tylko przypisuje żądanie do jednej z ustalonych akcji; wynik narzędzia nigdy do niego nie wraca. |
| Plan-Then-Execute | Plan (które narzędzia, w jakiej kolejności) jest ustalony, zanim agent przeczyta jakiekolwiek niezaufane dane. Dane mogą nadal kształtować argumenty, np. treść e-maila, ale nie mogą dodać akcji. |
| LLM Map-Reduce | Każdy niezaufany element trafia do odizolowanego subagenta, którego wyjście jest ograniczone (wartość logiczna, stały schemat); agregator nigdy nie widzi surowej treści. |
| Dual LLM | Uprzywilejowany model planuje i wywołuje narzędzia, ale nigdy nie widzi niezaufanego tekstu. Model w kwarantannie go czyta i oddaje tylko symboliczne odwołania. |
| Code-Then-Execute | Model pisze program, zanim zobaczy dane, a interpreter go wykonuje. |
| Context-Minimization | Tekst, który mógłby nieść instrukcje, np. oryginalny prompt, jest usuwany z kontekstu przed kolejnymi krokami. |

**CaMeL** [6] (Google DeepMind, 2025) łączy Code-Then-Execute z Dual LLM:
- Uprzywilejowany model pisze program na podstawie zaufanego zapytania.
- Model w kwarantannie parsuje niezaufane dane bez dostępu do narzędzi.
- Własny interpreter śledzi, skąd pochodzi każda wartość, i egzekwuje polityki przed każdym wywołaniem narzędzia.
- W benchmarku AgentDojo rozwiązał 77% zadań z dowodliwym bezpieczeństwem (provable security), wobec 84% bez żadnej obrony.

**Agents Rule of Two** [7] to zasada na poziomie sesji dla tego wszystkiego. Jedna sesja może mieć najwyżej dwie z trzech właściwości:
- [A] przetwarzanie niezaufanego wejścia;
- [B] dostęp do wrażliwych systemów lub prywatnych danych;
- [C] zmiana stanu lub komunikacja na zewnątrz.

Ograniczenie z Labu 6 to podręcznikowy przypadek. Sesja administratora czyta centrum pomocy [A], ma władzę nad kluczami organizacji [B] i może je zrotować [C]. Przy wszystkich trzech zasada wymaga nadzoru człowieka albo innej niezawodnej kontroli, a zmęczenie zatwierdzaniem usuwa dokładnie to.

**Kontrola ruchu wychodzącego (egress) i sandboxing** to najtańszy sposób na odcięcie nogi eksfiltracyjnej:
- Ruch wychodzący dopuszczaj przez allowlistę na poziomie infrastruktury (proxy), a nie w prompcie.
- Nie dawaj agentom ogólnego narzędzia „pobierz URL”.
- Uruchamiaj wygenerowany kod w sandboksie bez dostępu do sieci.
- Serwuj obrazy przez własne proxy.

**Rozszerz Lab 6:** najpierw napisz test odtwarzający, który nie przechodzi. To oskryptowane `search_kb`, a po nim `rotate_all_keys`, uruchomione w sesji `sess_dana` z `hitl_approved=True`. Potem dodaj śledzenie skażenia (taint tracking):
1. `run_agent` ustawia flagę, gdy do kontekstu trafi niezaufana treść.
2. Dopóki flaga jest ustawiona, `check_tool_policy` odmawia narzędzi zmieniających stan.
3. Jedyny wyjątek to świeże potwierdzenie, które pokazuje dokładną akcję i to, skąd przyszło żądanie.

---

## 3. Bezpieczeństwo MCP

Model Context Protocol sprawia, że każdy serwer narzędzi staje się częścią twojego łańcucha dostaw. Udokumentowano trzy rodzaje ataków:

- **Tool poisoning** [8]: instrukcje ukryte w opisie narzędzia, które model czyta, a użytkownik zwykle nie. Firma Invariant Labs opisała to 1 kwietnia 2025. Proof of concept to niewinnie wyglądające narzędzie `add`, którego opis kazał modelowi odczytać konfigurację MCP i prywatny klucz SSH użytkownika, a potem przekazać je serwerowi w ukrytym argumencie.
- **Rug pull** [8]: serwer zmienia opis narzędzia już po jego zatwierdzeniu.
- **Toxic agent flow** [9]: w maju 2025 zespół Invariant Labs pokazał, jak złośliwe publiczne zgłoszenie (issue) na GitHubie sprawia, że agent z oficjalnym serwerem GitHub MCP przenosi dane z prywatnego repozytorium do publicznego pull requesta. Opisano to jako problem architektury, a nie błąd serwera: sama poprawka po stronie serwera tego nie naprawi.

**Czego wymaga specyfikacja** (autoryzacja, rewizja 2026-07-28) [10]:
- OAuth 2.1.
- Klienci wysyłają parametr `resource` (RFC 8707), żeby przywiązać tokeny do jednego serwera MCP.
- Serwery sprawdzają, czy token został wydany dla nich.
- Wytyczne bezpieczeństwa specyfikacji wprost zakazują token passthrough, czyli przekazywania przez serwer otrzymanego tokenu do innej usługi.
- Te reguły dotyczą transportów HTTP. Lokalny serwer na stdio ich nie stosuje: bierze dane uwierzytelniające ze swojego środowiska, więc ogranicz je jak każdy inny sekret na tej maszynie.

**Lista kontrolna:**
- Przypinaj definicje narzędzi po hashu i przeglądaj diff przy każdej zmianie.
- Daj każdemu narzędziu osobny zakres zgodny z zasadą najmniejszych uprawnień, z krótkożyjącymi tokenami przypisanymi do odbiorcy (audience). Nigdy nie przekazuj dalej tokenów użytkowników.
- Uruchamiaj lokalne serwery w sandboksie: bez sieci, jeśli nie jest potrzebna, z allowlistą systemu plików.
- Traktuj opisy i wyniki narzędzi jako niezaufane wejście. Przechodzą przez ten sam tripwire i tę samą politykę narzędzi co artykuły z centrum pomocy w Labie 6.
- Zapisuj hash definicji narzędzia w trace'ach, żeby incydent dało się powiązać z wersją, która działała.
- Kategorie OWASP Agentic: ASI02 Tool Misuse, ASI03 Identity & Privilege Abuse, ASI04 Agentic Supply Chain Vulnerabilities [11].

---

## 4. RODO w systemach LLM

Prompty, trace'y, pobrane dokumenty i zbiory ewaluacyjne zawierające dane osobowe to przetwarzanie w rozumieniu RODO, niezależnie od tego, czy bierze w nim udział model.

- **Podstawy:** Potrzebujesz podstawy prawnej (art. 6), ograniczenia celu, minimalizacji danych (art. 5 ust. 1 lit. c) i ograniczenia przechowywania (art. 5 ust. 1 lit. e).
  - W praktyce maskuj dane osobowe, zanim trafią do trace'ów (Lab 2) i do API modelu (Lab 5), i ustaw retencję w narzędziu do obserwowalności.
- **DPIA (art. 35):** Wiele wdrożeń LLM, które przetwarzają dane osobowe na dużą skalę albo w nowy sposób, będzie wymagać oceny skutków dla ochrony danych. Zaangażuj IOD wcześnie, bo odpowiedź kształtuje architekturę.
- **Podmioty przetwarzające:** Dostawcy modeli i narzędzia SaaS do obserwowalności zwykle działają jako podmioty przetwarzające. Potrzebujesz umowy z art. 28, a przy transferach poza EOG mechanizmu transferu z rozdziału V. Zero data retention to zapis w umowie, a nie ustawienie, które można założyć.
- **Usuwanie danych a flywheel (art. 17):** Flywheel z Dnia 1 przenosi produkcyjne trace'y do Golden Dataset trzymanego w Gicie. Osoba, której dane dotyczą, może zażądać ich usunięcia.
  - Pseudonimizuj przed przeniesieniem.
  - Klucz do reidentyfikacji, jeśli istnieje, trzymaj poza Gitem.
  - Nie wpuszczaj prawdziwych danych osobowych do historii repozytorium, bo przepisywanie historii we wszystkich klonach jest bolesne.
- **Modele a dane osobowe:** Opinia EROD 28/2024 (17 grudnia 2024) [12] mówi trzy rzeczy:
  - Modeli trenowanych na danych osobowych nie zawsze można uznać za anonimowe.
  - Prawnie uzasadniony interes może być podstawą prawną, jeśli przejdzie trzyetapowy test.
  - Niezgodne z prawem przetwarzanie na etapie rozwoju może wpłynąć na to, czy model wolno wdrożyć.
- **Polskie dane osobowe:** Presidio ma rozpoznawacz (recognizer) numeru PESEL, a spaCy ma polskie pipeline'y. Dla innych identyfikatorów, np. NIP czy numeru dowodu osobistego, sprawdź aktualną listę rozpoznawaczy i tam, gdzie go brakuje, napisz własny z walidacją sumy kontrolnej. Mierz recall na polskim tekście tak, jak Lab 1 mierzy sędziego.
- **Zmiany w toku:** W listopadzie 2025 Komisja zaproponowała w pakiecie digital omnibus także zmiany w RODO, m.in. węższą definicję danych osobowych i wprost wskazany prawnie uzasadniony interes przy rozwijaniu i działaniu AI.
  - W listopadzie 2026 to nadal tylko propozycja. Rada przyjęła mandat negocjacyjny w październiku 2026, a Parlament nie przyjął jeszcze stanowiska [28] **(źródła wtórne, do weryfikacji)**.
  - Dopóki tekst nie zostanie przyjęty, obowiązuje obecne RODO bez zmian.

---

## 5. AI Act po Digital Omnibus

**Rozporządzenie (UE) 2026/1744**, czyli Digital Omnibus dotyczący AI, zostało opublikowane w Dzienniku Urzędowym 24 lipca 2026 i weszło w życie 27 lipca 2026 [13][14].

| Data | Co obowiązuje |
| :--- | :--- |
| 2 lutego 2025 | Praktyki zakazane i kompetencje w zakresie AI (art. 4), z pierwotnego harmonogramu |
| 2 sierpnia 2025 | Obowiązki dla modeli AI ogólnego przeznaczenia, z pierwotnego harmonogramu |
| 2 sierpnia 2026 | Obowiązki przejrzystości (art. 50): nieprzesunięte |
| 2 grudnia 2026 | Oznaczanie w formacie do odczytu maszynowego (art. 50 ust. 2) w systemach generatywnych wprowadzonych do obrotu przed 2 sierpnia 2026; dwa nowe zakazy (art. 5 ust. 1): systemy AI generujące intymne obrazy bez zgody albo materiały przedstawiające seksualne wykorzystywanie dzieci [13] |
| 2 grudnia 2027 | Obowiązki dla systemów wysokiego ryzyka z załącznika III (przesunięte z 2 sierpnia 2026) |
| 2 sierpnia 2028 | Obowiązki dla systemów wysokiego ryzyka w produktach z załącznika I (przesunięte z 2 sierpnia 2027) |

- **Art. 4 (kompetencje w zakresie AI)** [13][15]: Dostawcy i podmioty stosujące musieli podejmować środki w celu zapewnienia, w możliwie największym stopniu, odpowiedniego poziomu kompetencji w zakresie AI. Według nowego brzmienia mają podejmować środki wspierające rozwój tych kompetencji, bez obowiązku gwarantowania poziomu poszczególnych osób.
- **Art. 50 dla systemów z tego warsztatu:**
  - **Kto jest kim.** Zespół, który sam rozwija bota obsługi klienta i oddaje go do użytku pod własną nazwą, także na własny użytek, jest zwykle jego dostawcą (art. 3 pkt 3 i 11 rozporządzenia (UE) 2024/1689), a nie tylko podmiotem stosującym. Obowiązki dostawcy spadają wtedy na ten zespół.
  - **Dostawcy:** ludzie muszą wiedzieć, że rozmawiają z AI, chyba że to oczywiste (art. 50 ust. 1). Systemy generatywne muszą oznaczać swoje wyniki w formacie nadającym się do odczytu maszynowego, o ile jest to technicznie wykonalne (art. 50 ust. 2). Nie dotyczy to funkcji wspomagających standardową edycję, które nie zmieniają istotnie danych wejściowych.
  - **Podmioty stosujące:** ujawniaj deepfake'i oraz teksty wygenerowane przez AI publikowane w celu informowania opinii publicznej o sprawach leżących w interesie publicznym (art. 50 ust. 4).
  - **Jak oznaczać i etykietować:** Komisja zachęca do opracowania w tym celu kodeksów praktyk (art. 50 ust. 7). Przed wyborem techniki sprawdź ich aktualny status.
- **Wysokie ryzyko wynika z zastosowania, nie z technologii.** Wewnętrzny asystent odpowiadający na pytania na podstawie dokumentów HR (Lab 5) to inny przypadek niż system, który szereguje kandydatury albo decyduje o awansach. Ten drugi podlega załącznikowi III (zatrudnienie).
- Zanim zaplanujesz termin zgodności, przeczytaj rozporządzenie zmieniające [13] i skonsolidowany tekst AI Act w EUR-Lex.

---

## 6. Standardy i listy do śledzenia

- **OWASP Top 10 for LLM Applications 2026** [25], opublikowana 4 sierpnia 2026, zmienia numerację listy z 2025 roku:
  - Excessive Agency przesuwa się z LLM06 na LLM03, a Unbounded Consumption z LLM10 na LLM06.
  - Improper Output Handling spada z LLM05 na LLM10.
  - Kategorię System Prompt Leakage rozszerzono do LLM08 Hidden Context Exposure; obejmuje ona prompt systemowy, schematy narzędzi i pobrany tekst polityk.
  - Zanim porównasz kody, sprawdź, na którą edycję mapuje się dane narzędzie albo raport.
- **OWASP Top 10 for Agentic Applications for 2026** [11], opublikowana w grudniu 2025:
  - ASI01 Agent Goal Hijack
  - ASI02 Tool Misuse & Exploitation
  - ASI03 Identity & Privilege Abuse
  - ASI04 Agentic Supply Chain Vulnerabilities
  - ASI05 Unexpected Code Execution
  - ASI06 Memory & Context Poisoning
  - ASI07 Insecure Inter-Agent Communication
  - ASI08 Cascading Failures
  - ASI09 Human-Agent Trust Exploitation
  - ASI10 Rogue Agents
- **NIST AI RMF** z profilem dla generatywnej AI, NIST AI 600-1 [26], oraz **ISO/IEC 42001:2023** dla systemu zarządzania AI [27].
- **Rewizje specyfikacji MCP** [10]. Sekcja o autoryzacji zmieniała się wielokrotnie od 2025 roku, więc przypnij rewizję, którą implementują twoje serwery.

---

## 7. Narzędzia w 2026 roku: co się zmieniło

| Narzędzie | Zmiana | Data | Źródło |
| :--- | :--- | :--- | :--- |
| Langfuse | Przejęte przez ClickHouse. Rdzeń zostaje na licencji MIT, self-hosting jest nadal wspierany. | 16 stycznia 2026 | [16] |
| Helicone | Przejęte przez Mintlify. Tryb utrzymaniowy: poprawki bezpieczeństwa i nowe modele, bez nowych funkcji. | 3 marca 2026 | [17] |
| Promptfoo | OpenAI ogłosiło przejęcie, z zastrzeżeniem standardowych warunków zamknięcia transakcji. Promptfoo zostaje open source. Nie znaleziono informacji o zamknięciu transakcji **(do weryfikacji)**. | 9 marca 2026 | [18] |
| Arize (w tym Phoenix) | Firma Dynatrace ogłosiła przejęcie za 915 mln USD, a później poinformowała o jego zakończeniu. Phoenix zostaje open source. | 13 sierpnia 2026 | [19] |

Co z tego wynika dla twojego stosu:
- Emituj OpenTelemetry i dbaj o działający eksport OTLP.
- Trzymaj prompty, zbiory ewaluacyjne i logikę bramki we własnym repozytorium (Lab 3).
- Wiedz, kto jest właścicielem narzędzia, które ocenia model twojego dostawcy.

---

## 8. Incydenty, które warto znać

- **EchoLeak, CVE-2025-32711** [20][21]:
  - Podatność ujawniła firma Aim Security w czerwcu 2025.
  - Wystarczył jeden spreparowany e-mail do konta Microsoft 365. Nikt nie musiał go otwierać: przy późniejszym powiązanym pytaniu Copilot pobierał ten e-mail do kontekstu i wyprowadzał dane przez URL obrazka, który ładował się automatycznie.
  - Microsoft ocenił podatność jako krytyczną (CVSS 9.3) i naprawił ją po stronie serwera.
  - To produkcyjna wersja eksfiltracji przez Markdown z Labu 5.
- **Toxic agent flow w GitHub MCP** (maj 2025) [9]: cała triada w jednym demo. Niezaufany tekst zgłoszenia, prywatne repozytoria i publiczny pull request jako wyjście.
- **Moffatt v. Air Canada, 2024 BCCRT 149** (14 lutego 2024) [22]:
  - Chatbot linii lotniczej poinformował osobę kupującą bilet, że może wstecznie ubiegać się o taryfę żałobną, na co rzeczywista polityka nie pozwalała. Trybunał uznał Air Canada za odpowiedzialną za wprowadzenie w błąd przez zaniedbanie (negligent misrepresentation) i nakazał zapłatę 812,02 CAD tytułem odszkodowania, odsetek i opłat.
  - Trybunał stwierdził, że Air Canada nie dołożyła należytej staranności, aby jej chatbot podawał prawdziwe informacje („did not take reasonable care to ensure its chatbot was accurate”).
  - To orzeczenie w sprawie drobnych roszczeń, ale zasada jest jasna: firma odpowiada za to, co mówi jej bot.

---

## 9. Ćwiczenia do kontynuacji w domu

1. **Lab 1:**
   - Niech dwie osoby oznaczą te same 100 trace'ów z twojego systemu, po jednym trybie błędu naraz.
   - Policz ich zgodność (κ), zanim skalibrujesz sędziego, i raportuj każdą metrykę z przedziałem Wilsona.
2. **Lab 2:**
   - Zaimplementuj jedną poprawkę ogona z omówienia, timeout z zapamiętanym statusem albo żądanie hedgowane, i pokaż jej wpływ na P95.
   - Zinstrumentuj kod czystym SDK OpenTelemetry i wyślij te same spany przez OTLP do drugiego backendu (sekcja 7).
3. **Lab 3:** dodaj nocne zadanie, które uruchamia cały Golden Dataset pięć razy na żywym modelu i kończy się błędem, gdy pass^5 spadnie w którymkolwiek wycinku (slice).
4. **Lab 4:** zrób model zagrożeń jednego z własnych systemów z listami OWASP LLM i Agentic oraz Rule of Two i wypisz każdy serwer MCP, którego używa.
5. **Lab 5:**
   - Załaduj polskie rozpoznawacze Presidio i polski pipeline spaCy, a potem zmierz recall na 50 syntetycznych polskich dokumentach.
   - Dodaj jeden własny rozpoznawacz z walidacją sumy kontrolnej.
6. **Lab 6:**
   - Zaimplementuj śledzenie skażenia z sekcji 2, zaczynając od testu.
   - Jeśli twoja polityka danych dopuszcza zdalne generowanie w promptfoo, uruchom jego pluginy dostępne tylko zdalnie (`bola`, `bfla`, `indirect-prompt-injection`) [24] na tym samym celu i porównaj znaleziska z lokalnymi pluginami `policy`.

---

## Źródła

1. Yao et al., „τ-bench: A Benchmark for Tool-Agent-User Interaction in Real-World Domains”, arXiv:2406.12045 (2024). https://arxiv.org/abs/2406.12045
2. Sierra Research, repozytorium τ-bench (odesłanie do τ²-bench). https://github.com/sierra-research/tau-bench
3. Nasr et al., „The Attacker Moves Second: Stronger Adaptive Attacks Bypass Defenses against LLM Jailbreaks and Prompt Injections”, arXiv:2510.09023 (2025). https://arxiv.org/abs/2510.09023
4. Hines et al., „Defending Against Indirect Prompt Injection Attacks With Spotlighting”, arXiv:2403.14720 (2024). https://arxiv.org/abs/2403.14720
5. Beurer-Kellner et al., „Design Patterns for Securing LLM Agents against Prompt Injections”, arXiv:2506.08837 (2025). https://arxiv.org/abs/2506.08837
6. Debenedetti et al., „Defeating Prompt Injections by Design” (CaMeL), arXiv:2503.18813 (2025). https://arxiv.org/abs/2503.18813
7. Meta AI, „Agents Rule of Two: A Practical Approach to AI Agent Security” (31 października 2025). https://ai.meta.com/blog/practical-ai-agent-security/ ; komentarz: https://simonwillison.net/2025/Nov/2/new-prompt-injection-papers/
8. Invariant Labs, „MCP Security Notification: Tool Poisoning Attacks” (1 kwietnia 2025). https://invariantlabs.ai/blog/mcp-security-notification
9. Invariant Labs, „GitHub MCP Exploited: Accessing private repositories via MCP” (26 maja 2025). https://invariantlabs.ai/blog/mcp-github-vulnerability
10. Specyfikacja Model Context Protocol, Authorization, rewizja 2026-07-28. https://modelcontextprotocol.io/specification/2026-07-28/basic/authorization
11. OWASP GenAI Security Project, „OWASP Top 10 for Agentic Applications for 2026”. https://genai.owasp.org/resource/owasp-top-10-for-agentic-applications-for-2026/
12. EROD (EDPB), Opinion 28/2024 on certain data protection aspects related to the processing of personal data in the context of AI models (17 grudnia 2024). https://edpb.europa.eu/system/files/2024-12/edpb_opinion_202428_ai-models_en.pdf
13. Rozporządzenie (UE) 2026/1744 (Digital Omnibus on AI), ELI: http://data.europa.eu/eli/reg/2026/1744/oj ; tekst angielski: https://eur-lex.europa.eu/eli/reg/2026/1744/oj/eng ; AI Act, rozporządzenie (UE) 2024/1689: http://data.europa.eu/eli/reg/2024/1689/oj ; przegląd: https://artificialintelligenceact.eu/ai-act-explorer/digital-omnibus/
14. „Digital Omnibus on AI: Regulation (EU) 2026/1744 Is Published in the Official Journal” (źródło wtórne). https://www.nicfab.eu/en/posts/digital-omnibus-ai-official-journal/
15. „AI literacy: the Digital Omnibus rewrites Article 4 of the AI Act” (źródło wtórne). https://lawandtechnology.eu/en/ai-literacy-digital-omnibus-article-4-ai-act/
16. Langfuse, „Langfuse joins ClickHouse”. https://langfuse.com/blog/joining-clickhouse ; ClickHouse: https://clickhouse.com/blog/clickhouse-acquires-langfuse-open-source-llm-observability
17. Helicone, „Helicone joins Mintlify”. https://www.helicone.ai/blog/joining-mintlify ; Mintlify: https://mintlify.com/blog/mintlify-acquires-helicone
18. OpenAI, „OpenAI to acquire Promptfoo” (9 marca 2026). https://openai.com/index/openai-to-acquire-promptfoo/ ; Promptfoo: https://promptfoo.dev/blog/promptfoo-joining-openai
19. Dynatrace, „Dynatrace to acquire Arize” (13 sierpnia 2026). https://www.dynatrace.com/news/press-release/dynatrace-to-acquire-arize/ ; zakończenie: https://dynatrace.com/news/blog/dynatrace-completes-acquisition-of-arize
20. „EchoLeak: The First Real-World Zero-Click Prompt Injection Exploit in a Production LLM System”, arXiv:2509.10540. https://arxiv.org/abs/2509.10540
21. The Hacker News, „Zero-Click AI Vulnerability Exposes Microsoft 365 Copilot Data Without User Interaction” (czerwiec 2025). https://thehackernews.com/2025/06/zero-click-ai-vulnerability-exposes.html
22. Moffatt v. Air Canada, 2024 BCCRT 149. https://decisions.civilresolutionbc.ca/crt/crtd/en/525448/1/document.do ; komentarz: https://www.americanbar.org/groups/business_law/resources/business-law-today/2024-february/bc-tribunal-confirms-companies-remain-liable-information-provided-ai-chatbot/
23. Meta, karta modelu Llama Prompt Guard 2 (86M: wielojęzyczny, mDeBERTa-base; 22M: nastawiony na angielski). https://huggingface.co/meta-llama/Llama-Prompt-Guard-2-86M
24. Dokumentacja promptfoo: pluginy dostępne tylko zdalnie (`bola`, `bfla`, `indirect-prompt-injection`, `hijacking`) https://www.promptfoo.dev/docs/red-team/troubleshooting/data-handling ; prompt extraction https://www.promptfoo.dev/docs/red-team/plugins/prompt-extraction/ ; CLI https://www.promptfoo.dev/docs/usage/command-line ; ocenianie https://www.promptfoo.dev/docs/red-team/troubleshooting/grading-results
25. OWASP GenAI Security Project, „OWASP GenAI LLM Top 10 2026” (4 sierpnia 2026). https://genai.owasp.org/resource/owasp-genai-llm-top-10-2026/ ; lista i źródła: https://github.com/GenAI-Security-Project/GenAI-LLM-Top10
26. NIST, „Artificial Intelligence Risk Management Framework: Generative Artificial Intelligence Profile”, NIST AI 600-1 (lipiec 2024). https://doi.org/10.6028/NIST.AI.600-1
27. ISO/IEC 42001:2023, Artificial intelligence — Management system. https://www.iso.org/standard/42001
28. Stan prac nad zmianami RODO w pakiecie digital omnibus (źródła wtórne): https://www.nicfab.eu/en/posts/digital-omnibus-council/ ; https://eudigitalpolicy.eu/instruments/data-omnibus/
