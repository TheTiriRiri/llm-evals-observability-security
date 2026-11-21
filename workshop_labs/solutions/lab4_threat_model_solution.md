# Lab 4 Solution: Threat Model

## 1. Data Flows
- **Untrusted sources:** Slack messages, including external guests in shared channels; `Vendor-Submissions` pages uploaded by external vendors; Jira tickets and comments; any Confluence page that many people can edit.
- **Sensitive assets:** the `HR-Confidential` and `Security-Incidents` spaces (all in one shared index); the shared service-account token for Jira and Email; the prompts and retrieved chunks stored in the observability tool.
- **Sinks:** `send_email` (external communication); `create_jira_ticket` and comments (state change, readable by others); the bot's Slack replies (Markdown rendering, link unfurling, every member of the channel); the third-party observability tool.

Keep assets and sinks apart: HR data is what an attacker wants (the "private data" leg), the email tool and the Slack reply are how it gets out.

## 2. Attack Paths (top 3, plus 2 that teams usually miss)

| # | Attack Path (Source → Mechanism → Asset → Sink) | OWASP LLM 2026 | OWASP Agentic 2026 | Impact × Likelihood | Mitigation (which leg or property it removes) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| 1 | External guest asks in a shared channel → the shared index returns `HR-Confidential` chunks → the bot posts salary data in the channel | LLM02, LLM09 | ASI03 | 5 × 5 = **25** | Filter retrieval by the permissions of **everyone who can read the answer** (the channel's audience), not just the requester; or answer only in DMs and keep the bot out of shared channels. Enforced in the retrieval query, never in the system prompt. Removes the private-data leg. |
| 2 | Poisoned `Vendor-Submissions` page → indirect prompt injection → the model retrieves `HR-Confidential` → `send_email` to the attacker | LLM01, LLM03, LLM09 | ASI01, ASI02 | 5 × 4 = **20** | Per-user ACL filter in the vector query (private-data leg); recipient domain allowlist in the email tool, plus HITL that shows the exact recipients and body (exfiltration leg). Better still, no external email from a session that has read untrusted content (Rule of Two). |
| 3 | Poisoned page → the model writes a link with secrets in its query string → Slack unfurls the URL, i.e. Slack's servers fetch it → zero-click exfiltration | LLM10, LLM01 | ASI01 | 4 × 4 = **16** | Post replies with `unfurl_links` and `unfurl_media` disabled; strip or allowlist URLs in model output. A CSP is not an option: we do not control the Slack client. Removes the hidden exfiltration channel. |
| 4 | Any employee asks the bot to create tickets or send emails → it acts with the shared service-account token → actions the user could not take themselves (confused deputy) | LLM03 | ASI03 | 4 × 4 = **16** | Delegated per-user tokens (OAuth on-behalf-of) with minimal scopes, so every tool call runs with the requester's permissions and is audited per user. Limits the blast radius of every other path too. |
| 5 | Full prompts with retrieved HR chunks are logged to the SaaS observability tool → third-party exposure, long retention | LLM02 | — | 3 × 4 = **12** | Mask personal data before export, restrict who can read traces, set a retention TTL, and cover the vendor with a DPA and data residency. |

Also worth a line: **LLM06 Unbounded Consumption** (denial of wallet). Per-user rate and token budgets apply to any chatbot open to guests.

## 3. Notes for the Debrief
- Paths 2 and 3 are exfiltration (lethal trifecta). Path 4 is about integrity: an injected "close every ticket in project X" needs no private data at all. The Rule of Two covers it ([A] untrusted input + [B] a sensitive system + [C] a state change).
- HITL helps only if the approver sees exactly what will run, and approval fatigue sets in fast. That is why the allowlist stays as a deterministic check behind it (you will see the same in Lab 6).
- None of the mitigations relies on the model behaving well. Assume that sooner or later the injection succeeds, and make sure the system contains it.
