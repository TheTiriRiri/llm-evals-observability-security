"""Lab 6 Solution: object-level authorization, recipient allowlist, and a Base64-aware tripwire."""

from __future__ import annotations

import base64
import binascii
import re

from lab6_guardrails_and_redteam.guardrails import (
    ADMIN_TOOLS,
    KNOWN_TOOLS,
    MUTATING_TOOLS,
    ORG_EMAIL_DOMAINS,
    RESOURCE_ARG,
    RESOURCE_OWNERS,
    GuardrailResult,
    Principal,
    check_input_guardrail as base_input_check,
    check_output_guardrail,
)

# Exactly one address: "attacker@evil.example.net, bob@initech.example.com" must not pass.
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


def check_input_guardrail_strict(text: str) -> GuardrailResult:
    """Still a tripwire. Decoding Base64 closes the gap the scan's base64 strategy found, and nothing more:
    encodings and paraphrases are endless, so do not spend your security budget here."""
    base = base_input_check(text)
    if not base.allowed:
        return base
    # Grepping for fixed Base64 prefixes is useless: the encoding of "ignore" changes with case and
    # byte alignment ("Ignore" -> "SWdub3Jl", " ignore" -> "IGlnbm9yZQ=="), so decode and re-check.
    for segment in _decoded_base64_segments(text):
        if not base_input_check(segment).allowed:
            return GuardrailResult(False, "encoded_injection_suspected")
    return GuardrailResult(True, "ok")


def check_tool_policy_strict(tool_name: str, args: dict, principal: Principal, hitl_approved: bool = False) -> GuardrailResult:
    if tool_name not in KNOWN_TOOLS:
        return GuardrailResult(False, f"unknown_tool:{tool_name}")
    if tool_name in ADMIN_TOOLS and principal.role != "admin":
        return GuardrailResult(False, f"role_not_allowed:{principal.role}:{tool_name}")

    # Object-level authorization (BOLA). "Does not exist" and "not yours" get the same answer,
    # like a 404 for both, so the error cannot be used to enumerate other customers' IDs.
    arg = RESOURCE_ARG.get(tool_name)
    if arg is not None:
        object_id = str(args.get(arg, ""))
        if RESOURCE_OWNERS.get(object_id) != principal.org:
            return GuardrailResult(False, f"object_not_accessible:{object_id}")

    if tool_name == "send_external_email":
        recipient = str(args.get("to", "")).strip().lower()
        match = SINGLE_EMAIL.fullmatch(recipient)
        if not match or match.group(1) not in ORG_EMAIL_DOMAINS.get(principal.org, ()):
            return GuardrailResult(False, f"disallowed_recipient:{recipient}")

    # Human approval comes last: never ask a person to approve what the policy forbids anyway.
    if tool_name in MUTATING_TOOLS and not hitl_approved:
        return GuardrailResult(False, f"hitl_approval_required:{tool_name}")

    return GuardrailResult(True, "ok")


# Same names as lab6_guardrails_and_redteam/guardrails.py, so redteam_target.py can scan this
# implementation as a drop-in: GUARDRAILS_IMPL=solution promptfoo redteam eval ...
check_input_guardrail = check_input_guardrail_strict
check_tool_policy = check_tool_policy_strict
__all__ = ["check_input_guardrail", "check_output_guardrail", "check_tool_policy", "GuardrailResult", "Principal"]
