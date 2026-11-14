"""Lab 6 Starter: Layered Input, Tool-Execution (HITL), and Output Guardrails."""

from __future__ import annotations

import re
from dataclasses import dataclass

INJECTION_PATTERNS = [
    r"ignore\s+(all\s+)?previous\s+instructions",
    r"system\s+override",
    r"reveal\s+(your\s+)?system\s+prompt",
    r"bypass\s+(safety|guardrails|policy)",
]

MUTATING_TOOLS = {"delete_workspace", "send_external_email", "rotate_all_keys"}
SECRET_PATTERNS = [
    # API keys incl. prefixed formats: sk-proj-..., sk-svcacct-..., sk-ant-api03-..., sk-lf-...
    r"\bsk-[A-Za-z0-9_-]{16,}",
    r"\b\d{3}-\d{2}-\d{4}\b",  # SSN pattern
]


@dataclass
class GuardrailResult:
    allowed: bool
    reason: str


def check_input_guardrail(user_input: str) -> GuardrailResult:
    """Fast synchronous input check (runs before LLM)."""
    if len(user_input) > 4000:
        return GuardrailResult(False, "input_too_long")

    lowered = user_input.lower()
    for pat in INJECTION_PATTERNS:
        if re.search(pat, lowered):
            return GuardrailResult(False, f"prompt_injection_detected:{pat}")

    return GuardrailResult(True, "ok")


def check_tool_policy(tool_name: str, args: dict, hitl_approved: bool = False) -> GuardrailResult:
    """Policy & HITL gate for mutating or external-communication tools."""
    if tool_name in MUTATING_TOOLS and not hitl_approved:
        return GuardrailResult(False, f"hitl_approval_required:{tool_name}")

    # TODO (Lab 6): Add domain allowlist check if tool_name == "send_external_email"
    return GuardrailResult(True, "ok")


def check_output_guardrail(model_output: str) -> GuardrailResult:
    """Output leak check before sending response to user."""
    for pat in SECRET_PATTERNS:
        if re.search(pat, model_output):
            return GuardrailResult(False, "sensitive_pattern_leak")

    return GuardrailResult(True, "ok")
