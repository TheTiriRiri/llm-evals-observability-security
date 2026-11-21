# Target Architecture: Internal Ops Slack Assistant

```mermaid
flowchart LR
    U["Employee / External Guest in Slack"] --> BOT["Slack Bot Gateway"]
    BOT --> LLM["LLM Orchestrator"]
    LLM --> RAG["Confluence & Shared Drive Vector DB"]
    LLM --> JIRA["Jira Tool (Read/Write Tickets)"]
    LLM --> EMAIL["Email Tool (Send External Emails)"]
    RAG --> LLM
    LLM -. "full prompts, retrieved chunks, tool calls" .-> OBS["SaaS Observability Tool"]
```

## System Facts
- The Vector DB indexes **all** Confluence spaces (including `HR-Confidential`, `Security-Incidents`, and `Vendor-Submissions` where external vendors can upload docs).
- The Slack Bot runs with a single shared service-account token for Jira and Email.
- The bot answers in the channel where it was mentioned. Some channels are shared with external guests (Slack Connect).
- The LLM renders Markdown responses directly in Slack.
- There is currently no Human-in-the-Loop (HITL) confirmation before `send_email` or `create_jira_ticket`.
- For debugging, every request (full prompt, retrieved chunks, tool calls) is logged to a third-party SaaS observability tool.
