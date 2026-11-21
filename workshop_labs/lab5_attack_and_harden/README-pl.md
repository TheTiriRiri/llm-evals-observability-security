# Lab 5: Łamanie i utwardzanie podatnego asystenta (40 min)

## Część A: Atak (15 min)
1. Uruchom `python lab5_attack_and_harden/vulnerable_app.py`. Skrypt odgrywa trzy scenariusze z `attack_payloads.md`: stażystkę i kierowniczkę HR, każdą uwierzytelnioną przez sesję po stronie serwera.
2. Zaobserwuj podatności:
   - **Zbyt szerokie pobieranie dokumentów:** pytanie stażystki wciąga do promptu dane płacowe o klasyfikacji `hr_confidential`.
   - **Wyciek między tenantami:** ta sama stażystka dostaje warunki umowy innego klienta (Globex), bo wspólny indeks jest przeszukiwany bez filtra tenanta.
   - **Pośredni prompt injection + nadmierna autonomia (Excessive Agency):** strona dostawcy naszpikowana słowami kluczowymi pasuje do wielu zapytań i każe asystentowi wywołać `send_email` na adres atakującego.
   - **Eksfiltracja przez Markdown:** odpowiedź zawiera obrazek (bez kliknięcia: klient sam go pobiera) i link (jedno kliknięcie), oba z numerem SSN w URL-u.
   - **Brak redakcji PII:** imiona i nazwiska, adresy e-mail i SSN trafiają do zewnętrznego API modelu bez zmian.

## Część B: Obrona (25 min)
Uzupełnij funkcje oznaczone `TODO (Lab 5)` w `vulnerable_app.py`. Nie zmieniaj przepływu żądania (`handle_request`).
1. **Filtry tenanta i uprawnień w warstwie pobierania** (`retrieve_docs`), oparte na `Principal` ze zweryfikowanej sesji, a nigdy na wartościach z żądania lub od modelu.
2. **Redakcja PII za pomocą Microsoft Presidio** (`redact_pii`) z numerowanymi placeholderami (`<PERSON_1>`) i mapą, żeby odpowiedź dało się lokalnie odtworzyć (re-hydracja) dla użytkownika, który może ją zobaczyć.
3. **Deterministyczna autoryzacja narzędzi** (`send_email_tool`): sprawdzenie roli principala plus allowlista domen odbiorców.
4. **Sanityzacja wyjścia** (`sanitize_markdown`): usuń zewnętrzne obrazki i zneutralizuj linki do hostów spoza allowlisty.

Rozwiązanie wzorcowe: `python -m solutions.lab5_hardened_app`.

## Uwagi do omówienia
- Symulowany model wykonuje polecenia z injection w obu wersjach. Wersja utwardzona nie próbuje sprawić, żeby model zachowywał się dobrze; ogranicza to, do czego przejęty model może sięgnąć i co może zrobić.
- Hana może czytać dane płacowe, więc ACL przepuszcza dokument HR, a jej rola może wysyłać e-maile. Eksfiltrację zatrzymuje dopiero allowlista odbiorców. Jedna warstwa nigdy nie wystarcza.
- **Redakcja a uprawnione użycie:** dokument HR jest redagowany, zanim zobaczy go zewnętrzny model, a potem lokalnie odtwarzany dla Hany. Re-hydracja następuje po sanityzacji, więc prawdziwe wartości nigdy nie trafiają do URL-i. Dla każdej klasy danych zdecyduj, czy redakcja jest wymagana, czy wystarczy dostawca modelu z zerową retencją danych (ZDR) i umową powierzenia (DPA).
- **Presidio to NER „na tyle, na ile się da”, a nie gwarancja.** Zmierz jego recall na własnych danych, tak jak w dniu 1 mierzymy sędziego, i dodaj rozpoznawacze dla swojego języka i kraju. Presidio ma na przykład rozpoznawacz `PL_PESEL`, którego ten angielski pipeline nie ładuje.
- Zabawkowy indeks filtruje po wyszukaniu. Prawdziwa baza wektorowa musi stosować filtry tenanta i ACL wewnątrz zapytania; inaczej top-k wypełnią dokumenty, których wywołujący nie może zobaczyć.
- W kliencie, którego nie kontrolujesz, np. w Slacku, nie ustawisz CSP: wyłącz unfurling linków przy wysyłaniu wiadomości i sanityzuj tekst.
