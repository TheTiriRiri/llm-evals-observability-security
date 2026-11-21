# Lab 1 Solution: Failure Analysis (Dev Split) & Judge Calibration

## Failure modes observed in `dev` (`t01`–`t20`)

| # | Failure mode (axial code) | Traces | Share | Evaluator |
| :--- | :--- | :--- | :--- | :--- |
| 1 | **Unsupported or contradicted claims** | `t02`, `t05`, `t09`, `t10`, `t11`, `t13`, `t16`, `t18` | 8/20 (40%) | Binary LLM judge on `labels.faithfulness` |
| 2 | **Broken output format** (plain text instead of JSON) | `t03`, `t15` | 2/20 (10%) | `check_format`: `json.loads` + Pydantic ($0, ~1 ms) |
| 3 | **Missing or invalid citations** | `t07` (empty), `t20` (cites `B-11`, not retrieved) | 2/20 (10%) | `check_citations`: non-empty unless abstaining, IDs must be in the context |

Mode 1 is the most frequent and the most severe (it promises customers things the company does not offer). Its open codes split into sub-patterns that the judge prompt has to name explicitly:

- **Invented numbers or limits:** `t02` (30-day prorated refund), `t05` (100 MB).
- **Invented features or policy promises:** `t09` (free HIPAA BAA on Pro), `t18` ("Migrate Region" button).
- **Inverted policy:** `t13` (inactive seats are "free").
- **Answered beyond the context instead of abstaining:** `t10` (student discount the docs never mention).
- **Facts taken from the wrong document:** `t11` (workspace retention figure reported as audit-log retention).
- **Partially supported answers:** `t16` (first sentence correct, second contradicts `A-10`).

Two traces are worth discussing because they are *not* failures:

- `t08` is a correct abstention: the context does not cover on-premise, and the answer says so. A judge that rewards helpfulness marks it as bad.
- `t07` and `t20` are faithful answers with citation problems. They fail overall, but a faithfulness judge should PASS them. This is why every evaluator is scored against its own label, not `human_label`.

The mock judge only catches modes with invented numbers (`t02`, `t05`, `t10`). Inversions, mixed-up documents, partial support and invented features need a semantic evaluator.

## Reference binary judge prompt
See [`lab1_judge_prompt.txt`](./lab1_judge_prompt.txt). What changed compared with the starter prompt:

1. A claim-by-claim procedure with three named outcomes (SUPPORTED / CONTRADICTED / UNSUPPORTED), and an UNSUPPORTED definition that covers every sub-pattern above.
2. An explicit rule that "the documentation does not cover this" is faithful. Without it, judges tend to fail abstentions such as `t08`, `t23`, `t32` and `t38`.
3. Tone, length and helpfulness declared out of scope.
4. Reasoning written before the verdict, in the structured output.

## What to look for in the 1–5 baseline
With `--judge likert` and the PASS cut at 4, expect two kinds of disagreement:

- **False FAILs on correct abstentions** (`t08` on dev; `t23`, `t32`, `t38` on val): a vague quality rubric reads "the docs don't say" as an unhelpful answer.
- **False PASSes on fluent inventions** (`t09`, `t18` on dev; `t27`, `t36`, `t40` on val): confident, well-written answers score high whether or not the context supports them.

Moving the cut from 4 to 3 trades one kind of error for the other, which is the real problem with Likert scores used as gates. The exact counts depend on the model, so run it rather than trusting this list.

## Calibration and its limits
- On `val` the judge is scored on 19 traces with 8 faithfulness failures. Precision and recall ≥ 0.85 mean at most one miss and about one false alarm, and even 7/8 recall has a 95% interval of roughly 53–98%.
- Before relying on a judge in CI: label a few hundred traces, check that two human labelers agree with each other (kappa) and track the judge's agreement over time on fresh production samples.
- **Not covered by these evaluators:** a claim that is supported but cites the *wrong existing* document (attribution). If failure analysis on your own traffic shows it, add an attribution step to the judge or a second, separate check with its own label.
