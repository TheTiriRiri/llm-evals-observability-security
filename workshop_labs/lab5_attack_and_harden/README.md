# Lab 5: Breaking & Hardening a Vulnerable Assistant (40 min)

## Part A: Attack (15 min)
1. Run `python lab5_attack_and_harden/vulnerable_app.py`. It plays the three scenarios from `attack_payloads.md`: an intern and an HR manager, each authenticated through a server-side session.
2. Observe the vulnerabilities:
   - **Over-broad retrieval:** the intern's question pulls `hr_confidential` salary data into the prompt.
   - **Cross-tenant leak:** the same intern gets another customer's (Globex) contract terms, because the shared index is searched without a tenant filter.
   - **Indirect prompt injection + Excessive Agency:** a keyword-stuffed vendor page matches many queries and makes the assistant call `send_email` to an attacker.
   - **Markdown exfiltration:** the answer carries an image (zero-click: the client fetches it) and a link (one-click), both with the SSN in the URL.
   - **No PII redaction:** names, e-mail addresses and the SSN go to the external model API as they are.

## Part B: Defend (25 min)
Complete the `TODO (Lab 5)` functions in `vulnerable_app.py`. Do not change the request flow (`handle_request`).
1. **Tenant and clearance filters in retrieval** (`retrieve_docs`), based on the `Principal` from the verified session, never on values from the request or the model.
2. **PII redaction with Microsoft Presidio** (`redact_pii`), with numbered placeholders (`<PERSON_1>`) and a mapping, so the answer can be re-hydrated locally for the user who is allowed to see it.
3. **Deterministic tool authorization** (`send_email_tool`): a role check on the principal plus a recipient domain allowlist.
4. **Output sanitization** (`sanitize_markdown`): remove external images and neutralize links to hosts that are not on an allowlist.

Reference solution: `python -m solutions.lab5_hardened_app`.

## Notes for the Debrief
- The simulated model follows the injection in both versions. The hardened app does not try to make the model behave; it limits what a compromised model can reach and do.
- Hana may read salaries, so the ACL lets the HR document through, and her role may send e-mail. Only the recipient allowlist stops the exfiltration. One layer is never enough.
- **Redaction vs. authorized use:** the HR document is redacted before the external model sees it, then re-hydrated locally for Hana. Re-hydration runs after sanitization, so real values never end up in URLs. Decide per data class whether redaction is required, or whether a model vendor under zero data retention and a DPA is acceptable.
- **Presidio is best-effort NER, not a guarantee.** Measure its recall on your own data, the way Day 1 measures a judge, and add recognizers for your locale. For example, Presidio ships a `PL_PESEL` recognizer that this English pipeline does not load.
- The toy index filters after the search. A real vector DB must apply tenant and ACL filters inside the query; otherwise top-k fills up with documents the caller may not see.
- In a client you do not control, such as Slack, there is no CSP to set: disable link unfurling when posting and sanitize the text.
