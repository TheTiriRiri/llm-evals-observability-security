"""Lab 6 Solution: Guardrails with domain allowlist & Base64 smuggling check."""

from __future__ import annotations

import base64
import binascii
import re

from lab6_guardrails_and_redteam.guardrails import (
    MUTATING_TOOLS,
    GuardrailResult,
    check_input_guardrail as base_input_check,
    check_output_guardrail,
)

ALLOWED_EMAIL_DOMAINS = ("acme.example.com",)
# Exactly one address: "attacker@evil.example.net, bob@acme.example.com" must not pass.
SINGLE_EMAIL = re.compile(r"[a-z0-9._%+-]+@([a-z0-9-]+(?:\.[a-z0-9-]+)+)")
BASE64_TOKEN = re.compile(r"[A-Za-z0-9+/]{16,}={0,2}")


def _decoded_base64_segments(text: str) -> list[str]:
    """Decode every Base64-looking token that turns into readable UTF-8 text."""
    decoded = []
    for token in BASE64_TOKEN.findall(text):
        try:
            raw = base64.b64decode(token + "=" * (-len(token) % 4), validate=True)
            decoded.append(raw.decode("utf-8"))
        except (binascii.Error, UnicodeDecodeError):
            continue
    return decoded


def check_input_guardrail_strict(user_input: str) -> GuardrailResult:
    base = base_input_check(user_input)
    if not base.allowed:
        return base
    # Base64 smuggling: decode suspicious tokens and run the same checks on the plaintext.
    # (Grepping for fixed Base64 prefixes is useless: the encoding of "ignore" changes with
    # case and byte alignment, e.g. "Ignore" -> "SWdub3Jl", " ignore" -> "IGlnbm9yZQ==".)
    for segment in _decoded_base64_segments(user_input):
        if not base_input_check(segment).allowed:
            return GuardrailResult(False, "encoded_injection_suspected")
    return GuardrailResult(True, "ok")


def check_tool_policy_strict(tool_name: str, args: dict, hitl_approved: bool = False) -> GuardrailResult:
    if tool_name in MUTATING_TOOLS and not hitl_approved:
        return GuardrailResult(False, f"hitl_approval_required:{tool_name}")

    if tool_name == "send_external_email":
        recipient = str(args.get("to", "")).strip().lower()
        match = SINGLE_EMAIL.fullmatch(recipient)
        if not match or match.group(1) not in ALLOWED_EMAIL_DOMAINS:
            return GuardrailResult(False, f"disallowed_recipient_domain:{recipient}")

    return GuardrailResult(True, "ok")


# Same names as lab6_guardrails_and_redteam/guardrails.py, so redteam_target.py can scan this
# implementation as a drop-in: GUARDRAILS_IMPL=solution promptfoo redteam run ...
check_input_guardrail = check_input_guardrail_strict
check_tool_policy = check_tool_policy_strict
__all__ = ["check_input_guardrail", "check_output_guardrail", "check_tool_policy", "GuardrailResult"]
