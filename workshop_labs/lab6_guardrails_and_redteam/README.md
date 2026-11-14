# Lab 6: Runtime Guardrails & Automated Red Teaming (30 min)

## Goal
1. Implement layered runtime guardrails in `guardrails.py`:
   - **Input guardrail:** Fast deterministic + heuristic injection detector.
   - **Tool-execution guardrail:** Human-in-the-Loop (HITL) / policy gate on mutating tool calls (`delete_workspace`, `send_external_email`).
   - **Output guardrail:** PII/secret leak check before returning to the user.
2. Run `pytest lab6_guardrails_and_redteam/test_redteam_regressions.py -v` to verify your guardrails block known exploits.
3. Optionally run the promptfoo red-team scan (or `garak`) to probe for additional vulnerabilities and convert 2 discovered failures into permanent `pytest` regression cases.

## Run

```bash
pytest lab6_guardrails_and_redteam/test_redteam_regressions.py -v

# Optional red-team scan (requires OPENAI_API_KEY; run inside the activated .venv)
cd lab6_guardrails_and_redteam
PROMPTFOO_DISABLE_REDTEAM_REMOTE_GENERATION=true promptfoo redteam run -c promptfooconfig_redteam.yaml --env-file ../.env
promptfoo redteam report
```

The scan target is `redteam_target.py`: each attack passes through `check_input_guardrail`, then the LLM (with tools), then `check_tool_policy` for every tool call, then `check_output_guardrail`. Changes you make in `guardrails.py` show up in the next scan. promptfoo starts the target with the `python` on your `PATH` (override with `PROMPTFOO_PYTHON=/path/to/python`).

### Attack generation: local vs. promptfoo service

- **Local (command above, recommended for the workshop):** `PROMPTFOO_DISABLE_REDTEAM_REMOTE_GENERATION=true` makes promptfoo generate and grade attacks with your own `OPENAI_API_KEY`. No promptfoo account needed. The config uses only plugins and strategies that support this mode.
- **promptfoo generation service:** drop the variable. On the first run promptfoo asks for an email address and verifies it (one-time, interactive), so do this before the workshop, not in the middle of the lab. This mode unlocks remote-only extras such as the `hijacking` plugin and the `jailbreak:meta` strategy.

### What the scan exercises

The target gives the model real tool definitions and passes every tool call through `check_tool_policy` before anything runs (tools are simulated). Two switches:

- `REDTEAM_HITL_APPROVED=1` simulates a human who approves every request (approval fatigue). HITL no longer helps, so the email domain allowlist (your TODO in `check_tool_policy`) becomes the last line of defense.
- `GUARDRAILS_IMPL=solution` scans the reference solution instead of your `guardrails.py`, useful for a before/after comparison.
