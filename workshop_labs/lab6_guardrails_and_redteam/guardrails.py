"""Lab 6 Starter: layered runtime guardrails for the Acme Cloud support agent.

The three layers are not equally strong:
  1. check_input_guardrail is a TRIPWIRE. It stops lazy attacks and gives you telemetry, but
     paraphrases, other languages, encodings and indirect injection walk past it. A hit is a
     signal, never your security boundary.
  2. check_tool_policy is the BOUNDARY: deterministic code that decides, for every tool call,
     whether the signed-in principal may do this to this object. It has to hold when the model is
     fully compromised, because sooner or later it will be.
  3. check_output_guardrail is a last-chance leak check on what goes back to the user.
"""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class Principal:
    """The signed-in caller, resolved by your auth layer, never by the model or the request body."""

    user_id: str
    org: str
    role: str  # "member" or "admin"


@dataclass
class GuardrailResult:
    allowed: bool
    reason: str


INJECTION_PATTERNS = [
    r"ignore\s+(all\s+)?previous\s+instructions",
    r"system\s+override",
    r"reveal\s+(your\s+)?system\s+prompt",
    r"bypass\s+(safety|guardrails|policy)",
]

KNOWN_TOOLS = {"search_kb", "lookup_invoice", "send_external_email", "delete_workspace", "rotate_all_keys"}
MUTATING_TOOLS = {"send_external_email", "delete_workspace", "rotate_all_keys"}  # need human approval
ADMIN_TOOLS = {"delete_workspace", "rotate_all_keys"}  # need the admin role

# Stand-in for the system of record: which organization owns which object. In production, ask the
# service that owns the object, with the user's own token, instead of keeping a copy here.
RESOURCE_OWNERS = {
    "inv_1001": "initech",
    "inv_1002": "initech",
    "inv_2001": "globex",
    "ws_initech_main": "initech",
    "ws_globex_prod": "globex",
}
# The tool argument that names the object each tool acts on.
RESOURCE_ARG = {"lookup_invoice": "invoice_id", "delete_workspace": "workspace_id"}
# Verified e-mail domains of each organization: the only places its data may be sent.
ORG_EMAIL_DOMAINS = {"initech": ("initech.example.com",), "globex": ("globex.example.com",)}

SECRET_PATTERNS = [
    # API keys incl. prefixed formats: sk-proj-..., sk-svcacct-..., sk-ant-api03-..., sk-lf-...
    r"\bsk-[A-Za-z0-9_-]{16,}",
    r"\b\d{3}-\d{2}-\d{4}\b",  # SSN pattern
]


def check_input_guardrail(text: str) -> GuardrailResult:
    """Tripwire for obvious injection phrases. Runs on user input AND on retrieved documents.

    English regexes only: "Zignoruj poprzednie instrukcje", a paraphrase or a homoglyph passes.
    A trained classifier (e.g. Llama Prompt Guard 2) gives a better signal under the same rule:
    a detector cuts noise and feeds telemetry; check_tool_policy is the boundary.
    """
    if len(text) > 4000:
        return GuardrailResult(False, "input_too_long")

    lowered = text.lower()
    for pat in INJECTION_PATTERNS:
        if re.search(pat, lowered):
            return GuardrailResult(False, f"prompt_injection_detected:{pat}")

    return GuardrailResult(True, "ok")


def check_tool_policy(tool_name: str, args: dict, principal: Principal, hitl_approved: bool = False) -> GuardrailResult:
    """Deterministic gate for EVERY tool call (read-only ones included), evaluated outside the LLM."""
    if tool_name not in KNOWN_TOOLS:
        return GuardrailResult(False, f"unknown_tool:{tool_name}")  # deny by default
    if tool_name in ADMIN_TOOLS and principal.role != "admin":
        return GuardrailResult(False, f"role_not_allowed:{principal.role}:{tool_name}")

    # TODO (Lab 6) 1: Object-level authorization (BOLA). For a tool in RESOURCE_ARG, the object named in
    #   args must belong to principal.org according to RESOURCE_OWNERS. An unknown object is denied too
    #   (fail closed), with the same reason as a foreign one: otherwise the error tells an attacker
    #   which IDs exist.
    # TODO (Lab 6) 2: Recipient allowlist for send_external_email: exactly ONE address, whose domain is in
    #   ORG_EMAIL_DOMAINS[principal.org]. Watch for lists ("a@x.example, b@y.example"), look-alike domains
    #   ("initech.example.com.evil.example") and letter case ("Bob@Initech.Example.com" is fine).

    # Human approval comes last: never ask a person to approve what the policy forbids anyway.
    if tool_name in MUTATING_TOOLS and not hitl_approved:
        return GuardrailResult(False, f"hitl_approval_required:{tool_name}")

    return GuardrailResult(True, "ok")


def check_output_guardrail(model_output: str) -> GuardrailResult:
    """Last-chance leak check on the response before it reaches the user."""
    for pat in SECRET_PATTERNS:
        if re.search(pat, model_output):
            return GuardrailResult(False, "sensitive_pattern_leak")

    return GuardrailResult(True, "ok")
