# Threat Model Worksheet (Lab 4)

## 1. Data Flows
- Untrusted sources (who can write content that reaches the model?):
- Sensitive assets (what must not leak or be changed?):
- Sinks (where can data leave the system, or state change?):

## 2. Top 3 Attack Paths

| # | Attack Path (Source → Mechanism → Asset → Sink) | OWASP LLM Top 10 (2026) | OWASP Agentic Top 10 (2026) | Impact (1-5) × Likelihood (1-5) | Mitigation (which leg or property it removes) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| 1 | | | | | |
| 2 | | | | | |
| 3 | | | | | |

## 3. Controls That Are Not About the Model
- Identity: whose permissions does each tool call run with?
- Audience: who else can read the bot's answer?
- Logs: where do prompts and retrieved documents end up, and who can read them?

## Reference
- **Lethal trifecta** (data exfiltration): access to private data + exposure to untrusted content + a way to send data out. Remove one leg and the exfiltration path closes.
- **Agents Rule of Two** (any harmful action, including state changes): an agent session should have at most two of [A] untrusted input, [B] access to sensitive systems or private data, [C] the ability to change state or communicate externally.
- **OWASP Top 10 for LLM Applications 2026 (published 4 August 2026):** LLM01 Prompt Injection · LLM02 Sensitive Information Disclosure · LLM03 Excessive Agency · LLM04 Supply Chain · LLM05 Data and Model Poisoning · LLM06 Unbounded Consumption · LLM07 Misinformation · LLM08 Hidden Context Exposure · LLM09 Vector and Embedding Weaknesses · LLM10 Improper Output Handling. (The 2025 edition numbers these differently: e.g. Excessive Agency was LLM06, and LLM08 broadens the former System Prompt Leakage.)
- **OWASP Top 10 for Agentic Applications (2026, published December 2025):** ASI01 Agent Goal Hijack · ASI02 Tool Misuse & Exploitation · ASI03 Identity & Privilege Abuse · ASI04 Agentic Supply Chain Vulnerabilities · ASI05 Unexpected Code Execution · ASI06 Memory & Context Poisoning · ASI07 Insecure Inter-Agent Communication · ASI08 Cascading Failures · ASI09 Human-Agent Trust Exploitation · ASI10 Rogue Agents.
