# Lab 4: Modelowanie zagrożeń agentowej aplikacji RAG (20 min)

## Cel
W parach (12 min ćwiczenia + 8 min wspólnego omówienia):
1. Przejrzyj `architecture.md` (wewnętrzny asystent na Slacku z RAG na Confluence, narzędziami zapisu do Jiry/e-maila i narzędziem obserwowalności w modelu SaaS).
2. Rozpisz przepływy danych: **niezaufane źródła**, **wrażliwe aktywa** i **ujścia (sinks)**. Oddziel aktywa (to, czego chce atakujący) od ujść (którędy dane wychodzą albo co zostaje zmienione).
3. Wypełnij `threat_model_template.md`, opisując **3 konkretne ścieżki ataku**. Każdą zmapuj na OWASP Top 10 for LLM Applications (2026) i OWASP Top 10 for Agentic Applications (2026) oraz zaproponuj mitygację, która nie zależy od dobrego zachowania modelu. Przy każdej mitygacji wskaż, którą nogę „zabójczej triady” (lethal trifecta) albo którą właściwość z Rule of Two usuwa.
4. Odpowiedz na trzy pytania z sekcji 3 arkusza (tożsamość, odbiorcy, logi). Prowadzą do ścieżek, które zespoły zwykle pomijają.
