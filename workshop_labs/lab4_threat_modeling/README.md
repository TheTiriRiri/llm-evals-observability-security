# Lab 4: Threat Modeling an Agentic RAG App (20 min)

## Goal
In pairs (12 min exercise + 8 min group debrief):
1. Review `architecture.md` (an internal Slack assistant with Confluence RAG, Jira/Email write tools and a SaaS observability tool).
2. Map the data flows: **untrusted sources**, **sensitive assets** and **sinks**. Keep assets (what the attacker wants) apart from sinks (how it gets out or what gets changed).
3. Fill out `threat_model_template.md` with **3 concrete attack paths**. Map each to the OWASP Top 10 for LLM Applications (2026) and the OWASP Top 10 for Agentic Applications (2026), and propose a mitigation that does not depend on the model behaving well. For each mitigation, name the trifecta leg or Rule of Two property it removes.
4. Answer the three questions in section 3 of the worksheet (identity, audience, logs). They point at the paths teams usually miss.
