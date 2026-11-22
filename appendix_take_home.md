# Take-Home Appendix: What the Seven Hours Leave Out

**State as of:** November 2026. Facts were checked against the sources listed at the end. Where only secondary sources were available, or sources disagree, the text says **(to verify)**: check the primary text before you rely on it. Nothing here is legal advice.

Each section says why the topic matters and what to do about it. Section 9 lists exercises that extend the labs.

---

## 1. Evaluating Agents, Not Just Answers

Labs 1 and 3 grade single answers. An agent fails differently: it picks the wrong tool, passes wrong arguments, skips a confirmation, or ends in the wrong state while every individual message looks fine.

- **Grade the trajectory and the end state.**
  - *Trajectory:* which tools, which arguments, in which order, and what was refused.
  - *End state:* compare the system state after the conversation with the expected one. τ-bench grades agents by comparing the database state at the end of a conversation with an annotated goal state [1].
- **Measure consistency with pass^k.** pass^k counts a task as solved only if it succeeds in all k independent trials [1].
  - In the τ-bench paper, even gpt-4o solved under 50% of tasks, and its pass^8 was below 25% in the retail domain.
  - Gate on pass^k, not on pass@k: pass@k counts a task as solved if any one of k tries works, so it rewards an agent that only sometimes works.
  - The authors now point to τ²-bench as the maintained successor [2].
- **Simulated users are LLMs too.** Multi-turn evals need a user simulator. It can drift and leak the goal, so read its transcripts and calibrate it like any other judge.
- **Recipe:**
  1. Run failure analysis on agent traces (the span tree from Lab 2). Label tool-level failures: wrong tool, wrong arguments, missing confirmation, unnecessary call.
  2. Write deterministic checks first: tool names and argument schemas, forbidden tools, end-state assertions.
  3. Add an LLM judge only for what code cannot check, such as whether a refusal was justified.
  4. Run each case k times and report pass^k with an interval.
- **Extend Lab 6:** its replay tests already assert on the trajectory (`run.executed`) with a scripted model. Run the same assertions k times against a live model, and you have an agent eval.

---

## 2. Designing Agents That Survive Prompt Injection

Day 2 shows that detection is a signal, not a boundary.
- In "The Attacker Moves Second", adaptive attacks broke 12 published defenses, mostly with success rates above 90% [3].
- Spotlighting cut attack success from over 50% to under 2% against the static attacks in its own paper [4]. That is a useful reduction, not a guarantee.
- Classifiers are a signal too. Llama Prompt Guard 2 [23] comes as a multilingual 86M model and an English-focused 22M model, and Polish is not among the languages it was evaluated on. Measure any classifier on your own traffic before you rely on it.
- The remaining lever is architecture: make it impossible for injected text to cause harm, even when the model obeys it.

**Six design patterns** [5]. Their shared rule: once an agent has ingested untrusted input, that input must not be able to trigger side effects.

| Pattern | Idea |
| :--- | :--- |
| Action-Selector | The model only maps a request to one of a fixed set of actions; tool output never flows back into it. |
| Plan-Then-Execute | The plan (which tools, in which order) is fixed before any untrusted data is read. The data can still shape arguments, such as an email body, but cannot add actions. |
| LLM Map-Reduce | Each untrusted item goes to an isolated sub-agent whose output is constrained (a boolean, a fixed schema); the aggregator never sees raw content. |
| Dual LLM | A privileged model plans and calls tools but never sees untrusted text. A quarantined model reads it and hands back only symbolic references. |
| Code-Then-Execute | The model writes a program before it sees the data, and an interpreter runs it. |
| Context-Minimization | Text that could carry instructions, such as the original prompt, is removed from the context before later steps. |

**CaMeL** [6] (Google DeepMind, 2025) combines Code-Then-Execute with the Dual LLM:
- A privileged model writes a program from the trusted query.
- A quarantined model parses untrusted data without tool access.
- A custom interpreter tracks where every value came from and enforces policies before each tool call.
- On the AgentDojo benchmark it solved 77% of tasks with provable security, against 84% without any defense.

**The Agents Rule of Two** [7] is the session-level rule for all of this. Give one session at most two of three properties:
- [A] processing untrusted input;
- [B] access to sensitive systems or private data;
- [C] changing state or communicating externally.

The Lab 6 limit is the textbook case. An admin's session reads the help center [A], has power over the organization's keys [B] and can rotate them [C]. With all three, the rule requires supervision by a human or another reliable check, and approval fatigue removes exactly that.

**Egress control and sandboxing** are the cheapest way to cut the exfiltration leg:
- Allowlist outbound network traffic at the infrastructure level (a proxy), not in the prompt.
- Give agents no generic "fetch URL" tool.
- Run generated code in a sandbox without network access.
- Serve images through your own proxy.

**Extend Lab 6:** write the failing replay first. It is a scripted `search_kb` followed by `rotate_all_keys`, run in the `sess_dana` session with `hitl_approved=True`. Then add taint tracking:
1. `run_agent` sets a flag once untrusted content has entered the context.
2. While the flag is set, `check_tool_policy` denies state-changing tools.
3. The only exception is a fresh confirmation that shows the exact action and where the request came from.

---

## 3. MCP Security

The Model Context Protocol turns every tool server into part of your supply chain. Three attack shapes are documented:

- **Tool poisoning** [8]: instructions hidden in a tool's description, which the model reads but the user usually does not. Invariant Labs disclosed it on 1 April 2025. The proof of concept was a harmless-looking `add` tool whose description told the model to read the user's MCP configuration and SSH private key and pass them to the server in a hidden argument.
- **Rug pull** [8]: a server changes a tool's description after the user approved it.
- **Toxic agent flow** [9]: in May 2025 Invariant Labs showed a malicious public GitHub issue making an agent with the official GitHub MCP server leak private-repository data into a public pull request. They framed it as an architecture problem, not a bug in the server: a server-side patch alone cannot fix it.

**What the specification requires** (authorization, revision 2026-07-28) [10]:
- OAuth 2.1.
- Clients send the `resource` parameter (RFC 8707) to bind tokens to one MCP server.
- Servers validate that a token was issued for them.
- The specification's security guidance explicitly forbids token passthrough. That is a server forwarding the token it received to another service.
- These rules cover HTTP transports. A local server on stdio does not use them: it takes its credentials from its environment, so scope those like any other secret on that machine.

**Checklist:**
- Pin tool definitions by hash, and review the diff whenever they change.
- Give each tool its own least-privilege scope, with short-lived, audience-bound tokens. Never forward user tokens.
- Sandbox local servers: no network unless needed, a file-system allowlist.
- Treat tool descriptions and tool outputs as untrusted input. They go through the same tripwire and tool policy as the help-center articles in Lab 6.
- Record the tool-definition hash in your traces, so an incident can be traced to the version that ran.
- OWASP Agentic categories: ASI02 Tool Misuse, ASI03 Identity & Privilege Abuse, ASI04 Agentic Supply Chain Vulnerabilities [11].

---

## 4. GDPR for LLM Systems

Prompts, traces, retrieved documents and eval datasets that contain personal data are processing under the GDPR, whether or not a model is involved.

- **Basics:** You need a legal basis (Art. 6), purpose limitation, data minimization (Art. 5(1)(c)) and storage limitation (Art. 5(1)(e)).
  - In practice, mask personal data before it reaches traces (Lab 2) and the model API (Lab 5), and set retention in the observability tool.
- **DPIA (Art. 35):** Many LLM deployments that process personal data at scale or in new ways will need a data protection impact assessment. Involve your DPO early, because the answer shapes the architecture.
- **Processors:** Model vendors and SaaS observability tools usually act as processors. You need an Art. 28 agreement, and for transfers outside the EEA, a Chapter V transfer mechanism. Zero data retention is a contract term, not a setting you can assume.
- **Erasure vs. the flywheel (Art. 17):** The Day 1 flywheel promotes production traces into a golden dataset kept in Git. A person can ask for their data to be deleted.
  - Pseudonymize before promotion.
  - Keep any re-identification key outside Git.
  - Keep real personal data out of the repository history, because rewriting history across clones is painful.
- **Models and personal data:** EDPB Opinion 28/2024 (17 December 2024) [12] says three things:
  - Models trained on personal data cannot always be considered anonymous.
  - Legitimate interest can serve as a legal basis, if a three-step test is passed.
  - Unlawful processing during development can affect whether the model may be deployed.
- **Polish personal data:** Presidio ships a recognizer for the Polish PESEL number, and spaCy has Polish pipelines. For other identifiers, such as NIP or ID card numbers, check the current recognizer list and write custom recognizers with checksum validation where none exists. Measure recall on Polish text the same way Lab 1 measures a judge.
- **Pending changes:** In November 2025 the Commission also proposed GDPR amendments in its digital omnibus package, including a narrower definition of personal data and an explicit legitimate interest for developing and operating AI.
  - As of November 2026 they are still a proposal. The Council agreed its negotiating mandate in October 2026, and Parliament has not adopted its position [28] **(secondary sources, to verify)**.
  - Until a text is adopted, the current GDPR applies unchanged.

---

## 5. EU AI Act after the Digital Omnibus

The Digital Omnibus on AI, **Regulation (EU) 2026/1744**, was published in the Official Journal on 24 July 2026 and entered into force on 27 July 2026 [13][14].

| Date | What applies |
| :--- | :--- |
| 2 Feb 2025 | Prohibited practices and AI literacy (Art. 4), from the original timeline |
| 2 Aug 2025 | Obligations for general-purpose AI models, from the original timeline |
| 2 Aug 2026 | Transparency obligations (Art. 50): not postponed |
| 2 Dec 2026 | Machine-readable marking (Art. 50(2)) for generative systems placed on the market before 2 Aug 2026; two new prohibitions (Art. 5(1)): AI systems that generate non-consensual intimate imagery or child sexual abuse material [13] |
| 2 Dec 2027 | High-risk obligations for Annex III systems (postponed from 2 Aug 2026) |
| 2 Aug 2028 | High-risk obligations for systems in products under Annex I (postponed from 2 Aug 2027) |

- **Article 4 (AI literacy)** [13][15]: Providers and deployers had to take measures to "ensure, to their best extent, a sufficient level" of AI literacy. They must now "take measures to support the development of AI literacy", without having to guarantee any individual's level.
- **Article 50 for the systems in this workshop:**
  - **Who is who.** A team that develops its own support bot and puts it into service under its own name, even for its own use, is usually its provider (Art. 3(3) and 3(11) of Regulation (EU) 2024/1689), not only its deployer. The provider duties then fall on that team.
  - **Providers:** people must be told they are talking to an AI, unless it is obvious (Art. 50(1)). Generative systems must mark their output in a machine-readable way, as far as technically feasible (Art. 50(2)). This does not apply to assistive functions for standard editing that do not substantially alter the input.
  - **Deployers:** disclose deepfakes, and AI-generated text published to inform the public on matters of public interest (Art. 50(4)).
  - **How to mark and label:** the Commission encourages codes of practice for this (Art. 50(7)). Check their current status before you pick a technique.
- **High-risk is about use, not technology.** An internal assistant that answers questions from HR documents (Lab 5) is a different case from one that ranks candidates or decides promotions. The latter falls under Annex III (employment).
- Read the amending regulation [13] and the consolidated AI Act on EUR-Lex before you plan a compliance date.

---

## 6. Standards and Lists to Track

- **OWASP Top 10 for LLM Applications 2026** [25], published on 4 August 2026, renumbers the 2025 list:
  - Excessive Agency moves up from LLM06 to LLM03, and Unbounded Consumption from LLM10 to LLM06.
  - Improper Output Handling drops from LLM05 to LLM10.
  - System Prompt Leakage is broadened into LLM08 Hidden Context Exposure, which covers the system prompt, tool schemas and retrieved policy text.
  - Check which edition a tool or report maps to before you compare codes.
- **OWASP Top 10 for Agentic Applications for 2026** [11], published in December 2025:
  - ASI01 Agent Goal Hijack
  - ASI02 Tool Misuse & Exploitation
  - ASI03 Identity & Privilege Abuse
  - ASI04 Agentic Supply Chain Vulnerabilities
  - ASI05 Unexpected Code Execution
  - ASI06 Memory & Context Poisoning
  - ASI07 Insecure Inter-Agent Communication
  - ASI08 Cascading Failures
  - ASI09 Human-Agent Trust Exploitation
  - ASI10 Rogue Agents
- **NIST AI RMF** with its Generative AI Profile, NIST AI 600-1 [26], and **ISO/IEC 42001:2023** for an AI management system [27].
- **MCP specification revisions** [10]. The authorization section has changed repeatedly since 2025, so pin the revision your servers implement.

---

## 7. The 2026 Tool Landscape: What Changed

| Tool | Change | Date | Source |
| :--- | :--- | :--- | :--- |
| Langfuse | Acquired by ClickHouse. The core stays MIT-licensed and self-hosting remains supported. | 16 Jan 2026 | [16] |
| Helicone | Acquired by Mintlify. In maintenance mode: security fixes and new models, no new features. | 3 Mar 2026 | [17] |
| Promptfoo | OpenAI announced the acquisition, subject to customary closing conditions. Promptfoo stays open source. We found no closing notice **(to verify)**. | 9 Mar 2026 | [18] |
| Arize (incl. Phoenix) | Dynatrace announced the acquisition for $915M and later reported it as completed. Phoenix stays open source. | 13 Aug 2026 | [19] |

What follows for your stack:
- Emit OpenTelemetry and keep OTLP export working.
- Keep prompts, eval datasets and gate logic in your own repository (Lab 3).
- Know who owns the tool that grades your vendor's model.

---

## 8. Incidents Worth Knowing

- **EchoLeak, CVE-2025-32711** [20][21]:
  - Aim Security disclosed it in June 2025.
  - One crafted email to a Microsoft 365 user was enough. Nobody had to open it: when the user later asked Copilot a related question, Copilot retrieved the email and leaked data through an image URL that loaded automatically.
  - Microsoft rated it critical (CVSS 9.3) and fixed it server-side.
  - It is the production version of the Lab 5 Markdown exfiltration.
- **GitHub MCP toxic agent flow** (May 2025) [9]: the trifecta in one demo. Untrusted issue text, private repositories, and a public pull request as the exit.
- **Moffatt v. Air Canada, 2024 BCCRT 149** (14 February 2024) [22]:
  - The airline's chatbot told a customer they could claim a bereavement fare retroactively, which the actual policy did not allow. The tribunal found Air Canada liable for negligent misrepresentation and ordered it to pay CA$812.02 in damages, interest and fees.
  - The tribunal found that Air Canada "did not take reasonable care to ensure its chatbot was accurate".
  - It is a small-claims decision, but the principle is clear: the company owns what its bot says.

---

## 9. Exercises to Continue at Home

1. **Lab 1:**
   - Have two people label the same 100 of your own traces, one failure mode at a time.
   - Compute their κ before you calibrate a judge, and report every metric with a Wilson interval.
2. **Lab 2:**
   - Implement one tail fix from the debrief, a timeout with a cached status or a hedged request, and show its effect on P95.
   - Instrument with the plain OpenTelemetry SDK and send the same spans over OTLP to a second backend (section 7).
3. **Lab 3:** add a nightly job that runs the full golden set five times against the live model and fails when pass^5 drops on any slice.
4. **Lab 4:** threat-model one of your own systems with the OWASP LLM and Agentic lists and the Rule of Two, and list every MCP server it uses.
5. **Lab 5:**
   - Load Presidio's Polish recognizers and a Polish spaCy pipeline, and measure recall on 50 synthetic Polish documents.
   - Add one custom recognizer with checksum validation.
6. **Lab 6:**
   - Implement the taint tracking from section 2, test first.
   - If your data policy allows promptfoo's remote generation, run its remote-only plugins (`bola`, `bfla`, `indirect-prompt-injection`) [24] against the same target and compare the findings with the local `policy` plugins.

---

## Sources

1. Yao et al., "τ-bench: A Benchmark for Tool-Agent-User Interaction in Real-World Domains", arXiv:2406.12045 (2024). https://arxiv.org/abs/2406.12045
2. Sierra Research, τ-bench repository (pointer to τ²-bench). https://github.com/sierra-research/tau-bench
3. Nasr et al., "The Attacker Moves Second: Stronger Adaptive Attacks Bypass Defenses against LLM Jailbreaks and Prompt Injections", arXiv:2510.09023 (2025). https://arxiv.org/abs/2510.09023
4. Hines et al., "Defending Against Indirect Prompt Injection Attacks With Spotlighting", arXiv:2403.14720 (2024). https://arxiv.org/abs/2403.14720
5. Beurer-Kellner et al., "Design Patterns for Securing LLM Agents against Prompt Injections", arXiv:2506.08837 (2025). https://arxiv.org/abs/2506.08837
6. Debenedetti et al., "Defeating Prompt Injections by Design" (CaMeL), arXiv:2503.18813 (2025). https://arxiv.org/abs/2503.18813
7. Meta AI, "Agents Rule of Two: A Practical Approach to AI Agent Security" (31 October 2025). https://ai.meta.com/blog/practical-ai-agent-security/ ; commentary: https://simonwillison.net/2025/Nov/2/new-prompt-injection-papers/
8. Invariant Labs, "MCP Security Notification: Tool Poisoning Attacks" (1 April 2025). https://invariantlabs.ai/blog/mcp-security-notification
9. Invariant Labs, "GitHub MCP Exploited: Accessing private repositories via MCP" (26 May 2025). https://invariantlabs.ai/blog/mcp-github-vulnerability
10. Model Context Protocol specification, Authorization, revision 2026-07-28. https://modelcontextprotocol.io/specification/2026-07-28/basic/authorization
11. OWASP GenAI Security Project, "OWASP Top 10 for Agentic Applications for 2026". https://genai.owasp.org/resource/owasp-top-10-for-agentic-applications-for-2026/
12. EDPB, Opinion 28/2024 on certain data protection aspects related to the processing of personal data in the context of AI models (17 December 2024). https://edpb.europa.eu/system/files/2024-12/edpb_opinion_202428_ai-models_en.pdf
13. Regulation (EU) 2026/1744 (Digital Omnibus on AI), ELI: http://data.europa.eu/eli/reg/2026/1744/oj ; English text: https://eur-lex.europa.eu/eli/reg/2026/1744/oj/eng ; the AI Act, Regulation (EU) 2024/1689: http://data.europa.eu/eli/reg/2024/1689/oj ; overview: https://artificialintelligenceact.eu/ai-act-explorer/digital-omnibus/
14. "Digital Omnibus on AI: Regulation (EU) 2026/1744 Is Published in the Official Journal" (secondary). https://www.nicfab.eu/en/posts/digital-omnibus-ai-official-journal/
15. "AI literacy: the Digital Omnibus rewrites Article 4 of the AI Act" (secondary). https://lawandtechnology.eu/en/ai-literacy-digital-omnibus-article-4-ai-act/
16. Langfuse, "Langfuse joins ClickHouse". https://langfuse.com/blog/joining-clickhouse ; ClickHouse: https://clickhouse.com/blog/clickhouse-acquires-langfuse-open-source-llm-observability
17. Helicone, "Helicone joins Mintlify". https://www.helicone.ai/blog/joining-mintlify ; Mintlify: https://mintlify.com/blog/mintlify-acquires-helicone
18. OpenAI, "OpenAI to acquire Promptfoo" (9 March 2026). https://openai.com/index/openai-to-acquire-promptfoo/ ; Promptfoo: https://promptfoo.dev/blog/promptfoo-joining-openai
19. Dynatrace, "Dynatrace to acquire Arize" (13 August 2026). https://www.dynatrace.com/news/press-release/dynatrace-to-acquire-arize/ ; completion: https://dynatrace.com/news/blog/dynatrace-completes-acquisition-of-arize
20. "EchoLeak: The First Real-World Zero-Click Prompt Injection Exploit in a Production LLM System", arXiv:2509.10540. https://arxiv.org/abs/2509.10540
21. The Hacker News, "Zero-Click AI Vulnerability Exposes Microsoft 365 Copilot Data Without User Interaction" (June 2025). https://thehackernews.com/2025/06/zero-click-ai-vulnerability-exposes.html
22. Moffatt v. Air Canada, 2024 BCCRT 149. https://decisions.civilresolutionbc.ca/crt/crtd/en/525448/1/document.do ; commentary: https://www.americanbar.org/groups/business_law/resources/business-law-today/2024-february/bc-tribunal-confirms-companies-remain-liable-information-provided-ai-chatbot/
23. Meta, Llama Prompt Guard 2 model card (86M: multilingual mDeBERTa-base; 22M: English-focused). https://huggingface.co/meta-llama/Llama-Prompt-Guard-2-86M
24. promptfoo documentation: remote-only plugins (`bola`, `bfla`, `indirect-prompt-injection`, `hijacking`) https://www.promptfoo.dev/docs/red-team/troubleshooting/data-handling ; prompt extraction https://www.promptfoo.dev/docs/red-team/plugins/prompt-extraction/ ; CLI https://www.promptfoo.dev/docs/usage/command-line ; grading https://www.promptfoo.dev/docs/red-team/troubleshooting/grading-results
25. OWASP GenAI Security Project, "OWASP GenAI LLM Top 10 2026" (4 August 2026). https://genai.owasp.org/resource/owasp-genai-llm-top-10-2026/ ; list and source: https://github.com/GenAI-Security-Project/GenAI-LLM-Top10
26. NIST, "Artificial Intelligence Risk Management Framework: Generative Artificial Intelligence Profile", NIST AI 600-1 (July 2024). https://doi.org/10.6028/NIST.AI.600-1
27. ISO/IEC 42001:2023, Artificial intelligence — Management system. https://www.iso.org/standard/42001
28. Status of the GDPR amendments in the digital omnibus (secondary): https://www.nicfab.eu/en/posts/digital-omnibus-council/ ; https://eudigitalpolicy.eu/instruments/data-omnibus/
