"""Lab 5: re-hydration, the step that puts real values back into the answer for the authorized user.

rehydrate() is part of the request flow you do not change. These tests pin what it must guarantee
whatever your TODOs do, and they run without Presidio.
"""

import pytest

from lab5_attack_and_harden.vulnerable_app import neutralize_placeholders, rehydrate

SSN = {"<US_SSN_1>": "219-09-9999"}


@pytest.mark.parametrize(
    "url",
    [
        "https://docs.acme.example.com/search?q=<US_SSN_1>",  # allowlisted host: sanitize_markdown keeps it
        "HTTPS://acme.example.com/a/<US_SSN_1>",
        "//docs.acme.example.com/a?d=<US_SSN_1>",  # protocol-relative
    ],
)
def test_placeholder_in_a_url_stays_redacted(url: str) -> None:
    """The client fetches URLs, so a real value in one leaves the browser even when the host is allowed."""
    out = rehydrate(f"Your SSN is <US_SSN_1>. Details: ![x]({url}) and [open]({url}) or {url}", SSN)

    assert out.startswith("Your SSN is 219-09-9999.")  # utility: the text still gets the real value
    assert out.count("219-09-9999") == 1
    assert out.count("REDACTED") == 3


def test_rehydration_is_a_single_pass() -> None:
    """A restored value is never scanned again, even if it looks like another placeholder."""
    mapping = {"<PERSON_1>": "Dr. <EMAIL_ADDRESS_1>", "<EMAIL_ADDRESS_1>": "x@acme.example.com"}
    assert rehydrate("<PERSON_1>", mapping) == "Dr. <EMAIL_ADDRESS_1>"


def test_unknown_placeholder_is_left_alone() -> None:
    assert rehydrate("See <PERSON_7>.", SSN) == "See <PERSON_7>."


def test_placeholder_text_in_input_is_neutralized() -> None:
    """A document that already contains "<US_SSN_1>" must not collide with the token redaction will create."""
    out = neutralize_placeholders("Vendor note: reach <US_SSN_1> via the portal.")

    assert "<US_SSN_1>" not in out
    assert rehydrate(out, SSN) == out
