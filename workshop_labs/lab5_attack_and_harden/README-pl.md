# Lab 5: Łamanie i utwardzanie podatnego asystenta (40 min)

## Część A: Atak (15 min)
1. Uruchom `python lab5_attack_and_harden/vulnerable_app.py`, aby zobaczyć zwykłe zapytanie w porównaniu z podrzuconymi atakami z `attack_payloads.md`.
2. Zaobserwuj trzy podatności:
   - **Wyciek RAG między tenantami:** Użytkownik `public` pobiera `poufne` (`confidential`) dokumenty HR, ponieważ ACL są wspomniane wyłącznie w prompcie systemowym.
   - **Pośredni prompt injection + nadmierna autonomia (Excessive Agency):** Zatruty dokument nakłania asystenta do wywołania `send_email` na adres atakującego.
   - **Bezkliknięciowa eksfiltracja przez Markdown:** Asystent renderuje niezaufany link `![img](https://evil.example/...)`.

## Część B: Obrona (25 min)
Uzupełnij sekcje `TODO (Lab 5)` w `vulnerable_app.py`:
1. **Wymuś ACL bazy wektorowej w Pythonie** (`retrieve_docs`), zanim dokumenty w ogóle trafią do promptu LLM.
2. **Redaguj PII za pomocą Microsoft Presidio** (`redact_pii`) przed wysłaniem tekstu użytkownika do zewnętrznych API modeli lub do logów.
3. **Deterministyczna autoryzacja narzędzi** (`send_email_tool`) — sprawdzaj domenę odbiorcy względem allowlisty i blokuj niezatwierdzone wysyłki na zewnątrz.
4. **Sanityzuj wyjście Markdown** (`sanitize_markdown`) — usuwaj zewnętrzne tagi obrazków `![...](http...)`.
