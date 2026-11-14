"""Pre-workshop environment check. Run from workshop_labs/: `python check_env.py`.

Exits 1 if anything required for the offline/mock path of the labs is missing.
Warnings (live API key, Langfuse, promptfoo) only matter for the live variants.
"""

from __future__ import annotations

import importlib
import os
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
failures: list[str] = []
warnings: list[str] = []


def ok(msg: str) -> None:
    print(f"  [ OK ] {msg}")


def fail(msg: str) -> None:
    failures.append(msg)
    print(f"  [FAIL] {msg}")


def warn(msg: str) -> None:
    warnings.append(msg)
    print(f"  [WARN] {msg}")


def check_python() -> None:
    v = sys.version_info
    if v >= (3, 11):
        ok(f"Python {v.major}.{v.minor}.{v.micro}")
    else:
        fail(f"Python {v.major}.{v.minor} found, 3.11+ required")


def check_imports() -> None:
    for mod in ("openai", "pydantic", "pytest", "dotenv", "presidio_analyzer", "presidio_anonymizer"):
        try:
            importlib.import_module(mod)
            ok(f"import {mod}")
        except ImportError:
            fail(f"import {mod} failed - run `pip install -e .`")
    try:
        from importlib.metadata import version

        lf = version("langfuse")
        if lf.split(".")[0] == "5":
            ok(f"langfuse {lf}")
        else:
            fail(f"langfuse {lf} installed, Lab 2 is written for langfuse 5.x - run `pip install -e .`")
    except Exception:
        fail("langfuse not installed - run `pip install -e .`")


def check_spacy_model() -> None:
    try:
        import spacy.util

        if spacy.util.is_package("en_core_web_sm"):
            ok("spaCy model en_core_web_sm (Lab 5)")
        else:
            fail("spaCy model en_core_web_sm missing - run `python -m spacy download en_core_web_sm`")
    except ImportError:
        fail("spaCy not installed - run `pip install -e .`")


def check_lab_packages() -> None:
    # Import from a neutral directory in a fresh interpreter. A plain import here would succeed
    # even without the install (this script's directory and the generated *.egg-info sit on
    # sys.path), while `python solutions/...` would still fail with ModuleNotFoundError.
    import tempfile

    pkgs = ["lab1_evals_and_judge", "lab2_observability", "lab3_ci_gate",
            "lab5_attack_and_harden", "lab6_guardrails_and_redteam", "solutions"]
    code = "import " + ", ".join(pkgs)
    result = subprocess.run([sys.executable, "-c", code], cwd=tempfile.gettempdir(), capture_output=True, text=True)
    if result.returncode == 0:
        ok("lab packages installed (pip install -e .)")
    else:
        fail("lab packages not importable outside workshop_labs/ - run `pip install -e .` from workshop_labs/")


def check_env_file() -> None:
    env = HERE / ".env"
    if not env.exists():
        warn(".env missing - run `cp .env.example .env` (needed only for live runs)")
        return
    from dotenv import dotenv_values

    values = dotenv_values(env)
    key = values.get("OPENAI_API_KEY") or ""
    if not key or key.startswith("sk-your"):
        warn("OPENAI_API_KEY is still the placeholder - mock modes work, live judge/red team will not")
    else:
        ok("OPENAI_API_KEY set")
    lf_public = values.get("LANGFUSE_PUBLIC_KEY") or ""
    lf_secret = values.get("LANGFUSE_SECRET_KEY") or ""
    if lf_public.startswith("pk-lf-your") and lf_secret.startswith("sk-lf-your"):
        warn("Langfuse keys not set - Lab 2 will print local traces only (optional)")
    elif not lf_public or not lf_secret or lf_public.startswith("pk-lf-your") or lf_secret.startswith("sk-lf-your"):
        warn("only one Langfuse key is set - Lab 2 needs both LANGFUSE_PUBLIC_KEY and LANGFUSE_SECRET_KEY")
    else:
        ok("Langfuse keys set (not validated against the server)")


def check_promptfoo() -> None:
    if not shutil.which("node"):
        warn("node not found - Labs 3 and 6 (promptfoo parts) need Node.js 18+")
        return
    node = subprocess.run(["node", "--version"], capture_output=True, text=True).stdout.strip()
    ok(f"node {node}")
    if shutil.which("promptfoo"):
        ok("promptfoo on PATH")
    else:
        warn("promptfoo not on PATH - run `npm install -g promptfoo` (Labs 3 and 6)")


def main() -> int:
    os.chdir(HERE)
    print("Workshop environment check\n")
    check_python()
    check_imports()
    check_spacy_model()
    check_lab_packages()
    check_env_file()
    check_promptfoo()
    print()
    if failures:
        print(f"{len(failures)} problem(s) must be fixed before the workshop.")
        return 1
    print(f"Ready for the offline labs ({len(warnings)} warning(s) affect only the live variants).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
