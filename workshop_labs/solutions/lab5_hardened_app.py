"""Lab 5 Solution: Hardened RAG + Tool Assistant."""

from __future__ import annotations

import re
from functools import lru_cache
from urllib.parse import urlsplit

from lab5_attack_and_harden.vulnerable_app import (
    EMAIL_OUTBOX,
    Principal,
    demo,
    rehydrate,
    resolve_principal,
    similarity_search,
    simulated_llm,
)

ALLOWED_EMAIL_DOMAINS = ("acme.example.com",)
EMAIL_SENDER_ROLES = {"hr_manager", "support_lead"}
ALLOWED_LINK_HOSTS = ("acme.example.com", "docs.acme.example.com")
PII_ENTITIES = ["EMAIL_ADDRESS", "PHONE_NUMBER", "US_SSN", "PERSON"]
# Exactly one address, no separators: "attacker@evil.example.net, bob@acme.example.com" must not pass.
SINGLE_EMAIL = re.compile(r"[a-z0-9._%+-]+@([a-z0-9-]+(?:\.[a-z0-9-]+)+)")
# Markdown image / link with an absolute or protocol-relative URL, any letter case (HTTPS://, //host/...).
MD_IMAGE = re.compile(r"!\[[^\]]*\]\(\s*((?:[a-z][a-z0-9+.-]*:)?//[^)\s]*)[^)]*\)", re.IGNORECASE)
MD_LINK = re.compile(r"\[([^\]]*)\]\(\s*((?:[a-z][a-z0-9+.-]*:)?//[^)\s]*)[^)]*\)", re.IGNORECASE)
SPACY_MODEL = "en_core_web_sm"


@lru_cache(maxsize=1)
def _presidio_engines():
    """Build Presidio engines once per process.

    Loading the spaCy model takes seconds, so never create AnalyzerEngine() per request.
    The model is pinned explicitly: Presidio's default config wants `en_core_web_lg`
    and silently downloads it (~400 MB) when missing.
    """
    import spacy
    from presidio_analyzer import AnalyzerEngine
    from presidio_analyzer.nlp_engine import NlpEngineProvider
    from presidio_anonymizer import AnonymizerEngine

    if not spacy.util.is_package(SPACY_MODEL):
        raise RuntimeError(f"spaCy model '{SPACY_MODEL}' is missing. Run: python -m spacy download {SPACY_MODEL}")

    nlp_engine = NlpEngineProvider(
        nlp_configuration={
            "nlp_engine_name": "spacy",
            "models": [{"lang_code": "en", "model_name": SPACY_MODEL}],
        }
    ).create_engine()
    return AnalyzerEngine(nlp_engine=nlp_engine, supported_languages=["en"]), AnonymizerEngine()


def retrieve_docs(query: str, principal: Principal) -> list[dict]:
    """Tenant isolation first, then document-level clearances, both before prompt assembly.

    The toy index filters after the search; a real vector DB must apply both as metadata filters
    inside the query, or top-k can fill up with documents the caller is not allowed to see.
    """
    return [
        d for d in similarity_search(query)
        if d["tenant"] == principal.tenant and d["access_level"] in principal.clearances
    ]


def redact_pii(text: str, mapping: dict[str, str] | None = None) -> tuple[str, dict[str, str]]:
    """Replace PII with numbered placeholders; return (redacted_text, placeholder -> original).

    The same value always gets the same token (also across calls that share `mapping`),
    so the model can still tell people apart without seeing who they are.
    """
    from presidio_anonymizer.entities import OperatorConfig

    mapping = {} if mapping is None else mapping
    analyzer, anonymizer = _presidio_engines()

    def tokenizer(entity: str):
        def to_token(original: str) -> str:
            for token, value in mapping.items():
                if value == original:
                    return token
            n = sum(1 for token in mapping if token.startswith(f"<{entity}_")) + 1
            token = f"<{entity}_{n}>"
            mapping[token] = original
            return token

        return to_token

    results = analyzer.analyze(text=text, entities=PII_ENTITIES, language="en")
    operators = {e: OperatorConfig("custom", {"lambda": tokenizer(e)}) for e in PII_ENTITIES}
    return anonymizer.anonymize(text=text, analyzer_results=results, operators=operators).text, mapping


def send_email_tool(to: str, body: str, principal: Principal) -> str:
    """Deterministic authorization & recipient domain allowlist outside the LLM."""
    if principal.role not in EMAIL_SENDER_ROLES:
        raise PermissionError(f"Role '{principal.role}' is not authorized to send emails.")
    match = SINGLE_EMAIL.fullmatch(to.strip().lower())
    if not match or match.group(1) not in ALLOWED_EMAIL_DOMAINS:
        raise ValueError(f"Blocked email recipient: {to!r} (one address in {ALLOWED_EMAIL_DOMAINS} required)")

    EMAIL_OUTBOX.append({"to": to, "body": body})
    return f"Email sent to {to}"


def _allowed_host(url: str) -> bool:
    host = (urlsplit(url if "://" in url else "https:" + url).hostname or "").lower()
    return any(host == h or host.endswith("." + h) for h in ALLOWED_LINK_HOSTS)


def sanitize_markdown(output: str) -> str:
    """Drop external images (zero-click) and neutralize links to non-allowlisted hosts (one-click).

    A regex is a workshop-sized defense. In production, render Markdown with a parser and an
    image/link host allowlist, and back it with a CSP (`img-src 'self'`) in clients you control.
    For third-party clients such as Slack, also disable link unfurling when posting.
    """
    output = MD_IMAGE.sub(lambda m: m.group(0) if _allowed_host(m.group(1)) else "[external image removed]", output)
    return MD_LINK.sub(lambda m: m.group(0) if _allowed_host(m.group(2)) else f"{m.group(1)} [link removed]", output)


def hardened_handle_request(session_token: str, user_query: str) -> str:
    principal = resolve_principal(session_token)
    docs = retrieve_docs(user_query, principal)

    # Everything that leaves the process (LLM API, logs, traces) is redacted first.
    clean_query, mapping = redact_pii(user_query)
    clean_context, mapping = redact_pii("\n".join(d["text"] for d in docs), mapping)
    print(f"  [sent to LLM] query={clean_query!r}")
    print(f"  [sent to LLM] context docs={[d['id'] for d in docs]}")

    raw_answer, tool_calls = simulated_llm(clean_context)  # assume the model WILL follow the injection
    for tool, recipient in tool_calls:
        try:
            send_email_tool(to=recipient, body=f"Leaked: {clean_context[:160]}", principal=principal)
        except (PermissionError, ValueError) as exc:
            print(f"  [tool blocked] {exc}")

    # Sanitize first, then re-hydrate: never put real values back into URLs the client will fetch.
    return rehydrate(sanitize_markdown(raw_answer), mapping)


if __name__ == "__main__":
    print("=== Running Hardened Assistant Demo ===")
    demo(handler=hardened_handle_request)
