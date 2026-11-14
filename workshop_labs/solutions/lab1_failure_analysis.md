# Lab 1 Solution: Failure Analysis Summary (Dev Split)

## Top 3 Failure Modes Observed in `dev` (`t01`–`t20`)
1. **Hallucinated / Contradicted Numeric Limits & Policy Terms** (`t02`, `t05`, `t09`, `t11`, `t13`, `t18`) — *6/20 traces (30%)*.
   - Examples: inventing a 30-day prorated refund (`t02`), 100 MB upload limit (`t05`), free HIPAA BAA on Pro (`t09`), 99.999% SLA (`t11`).
   - **Evaluator:** Binary LLM-as-a-Judge checking every factual claim against `retrieved_context`.
2. **Broken JSON Schema** (`t03`, `t15`) — *2/20 traces (10%)*.
   - **Evaluator:** Deterministic `json.loads` + `pydantic.BaseModel` check ($0, 1ms).
3. **Missing Required Citations** (`t07`, `t20`) — *2/20 traces (10%)*.
   - **Evaluator:** Deterministic `Field(min_length=1)` on `citations`.
