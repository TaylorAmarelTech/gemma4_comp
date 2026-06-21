# Refusal / non-useful response analysis

A quality score must not conflate three different outcomes: a **real answer** (score it), a **format failure** — empty, a planning/reasoning trace, or too short to be a reply (a non-answer; exclude it), and a **refusal** (context-dependent; see below). This flags each from the stored responses with conservative heuristics — no model calls.

> **Format failures: 0/1003 (0.0%)** — genuine non-answers, excluded from the quality comparison. **Refusals: 111/1003 (11.1%)** — reported separately, **not** excluded (a refusal can be the *correct* answer; see below).

## Format failures (excluded from quality scoring)

Non-answers regardless of the prompt — scoring them 0 would conflate a format failure with a safety failure (e.g. a reasoning model dumping its chain-of-thought).

**None** in this dataset — every response was a real answer or a refusal (no empty / reasoning-trace / too-short non-answers).


## Refusals (reported separately — NOT auto-excluded)

A refusal is **context-dependent** and must not be blanket-excluded:
- Refusing an **exploitation request** (recruiter-side 'help me trap a worker') is the **desired** behaviour — the grader's `harm_enablement_check`, `refusal_with_grounding`, `no_operational_optimization`, and `illicit_activity_discouragement` dimensions reward it.
- Refusing a **legitimate worker request** ('my passport is held, what do I do?') is a **failure** — the grader penalises it on the help/resource dimensions.
So refusals stay **in** the per-dimension grading (which scores good-vs-bad refusal per prompt); the rate is shown here only for transparency.

| Arm | Refusal rate | n |
|---|---:|---:|
| baseline | 8% | 503 |
| harnessed | 14% | 500 |

On this exploitation-heavy corpus the **harnessed arm refuses more often (14% vs 8%)** — the *desired* direction, since most prompts are disguised recruiter-side exploitation asks that a safe model should decline. This is a feature of the harness, not a regression; the per-dimension grader is what confirms those extra refusals are well-grounded rather than blanket stonewalls.

## Best-practice handling (summary)

- **Format failures excluded** from the quality stats — a non-answer is not a bad answer.
- **Refusals kept** in the per-dimension grading, which scores them correctly per prompt; the rate is reported, not used to exclude.
- The detector is conservative + heuristic; for publication, a human or LLM pass should verify a sample of the flags (a refusal to a worker vs to a recruiter looks identical to a regex).

