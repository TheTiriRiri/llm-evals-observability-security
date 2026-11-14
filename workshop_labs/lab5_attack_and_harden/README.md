# Lab 5: Breaking & Hardening a Vulnerable Assistant (40 min)

## Part A: Attack (15 min)
1. Run `python lab5_attack_and_harden/vulnerable_app.py` to see a normal query vs. the planted attacks in `attack_payloads.md`.
2. Observe three vulnerabilities:
   - **Cross-tenant RAG leak:** A `public` user retrieves `confidential` HR docs because ACLs are only mentioned in the system prompt.
   - **Indirect prompt injection + Excessive Agency:** A poisoned document tricks the assistant into calling `send_email` to an attacker address.
   - **Zero-click Markdown exfiltration:** The assistant renders an untrusted `![img](https://evil.example/...)` link.

## Part B: Defend (25 min)
Complete the `TODO (Lab 5)` sections in `vulnerable_app.py`:
1. **Enforce Vector DB ACLs in Python** (`retrieve_docs`) before documents ever reach the LLM prompt.
2. **Redact PII with Microsoft Presidio** (`redact_pii`) before sending user text to external LLM APIs or logs.
3. **Deterministic Tool AuthZ** (`send_email_tool`)—validate recipient domain allowlist and block unapproved external sends.
4. **Sanitize Markdown Output** (`sanitize_markdown`)—strip external image tags `![...](http...)`.
