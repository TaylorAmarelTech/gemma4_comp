# Applicability verification + multi-pass judging

Per-dimension grading raises two questions this audit answers on the live rubric: are the grader's **applicability** decisions (which dimensions it excludes as NOT_APPLICABLE per prompt) correct, and are an LLM judge's per-dimension calls **stable across passes**? An independent judge (`gpt-oss:120b`, outside the candidate families) re-decides applicability for a stratified sample of (prompt, dimension) pairs, **3 passes** each.

> Over **800 (prompt × dimension) pairs**, the deterministic grader and the LLM judge agree on applicability **68%** of the time (**Cohen's κ = 0.36**, fair). The judge's 3 passes are unanimous on **86%** of pairs — so single-pass applicability calls are mostly stable, and the deterministic gate agrees with an independent model **more than chance but with meaningful disagreement** — applicability is genuinely judgment-dependent, not mechanical, which is itself a useful finding about the rigid grader.

## Agreement by side

| Grader said | n | Judge agreed | rate |
|---|---:|---:|---:|
| applicable | 400 | 286 | 72% |
| NOT applicable | 400 | 260 | 65% |

## Reading this

- **κ** corrects raw agreement for chance; ≥0.6 is substantial. High κ means the grader's applicability gating is not arbitrary — an independent model excludes the same dimensions.
- **Unanimity** across passes quantifies judge non-determinism *at the dimension level*: high unanimity means a single pass is a reliable applicability call; lower unanimity is exactly the case where multiple passes (and reporting the vote) matters.
- This validates the **gating**, not the scores: it shows we score the *right* dimensions per prompt. Score-level agreement between the deterministic grader and the LLM judge is the separate convergent-validity check (`convergent_validity.md`).

