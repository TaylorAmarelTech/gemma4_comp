# Writeup snippet — DueCare Kaggle Community Benchmark

> Paste-ready prose for `docs/writeup_draft.md`. Numbers are derived
> from the live Kaggle run on 2026-05-20 (v4 task notebook). Re-run
> `python scripts/validate_benchmark.py` and update this file when
> the corpus or criteria change.

---

## Short version (one paragraph)

DueCare publishes a Kaggle Community Benchmark
([`new-benchmark-task-443d1`](https://www.kaggle.com/code/taylorsamarel/new-benchmark-task-443d1))
that scores any LLM on 23 migrant-worker safety scenarios using a
Kaggle-hosted judge LLM. Each scenario is checked against six versioned
natural-language criteria — refusal correctness, no operational uplift,
legal grounding, exploitation indicators, evidence preservation, and
privacy minimization — and each criterion becomes one
`kbench.assertions.assert_true` checkpoint. The corpus is intentionally
not generic safety: 10 of 23 rows are statute-specific fee-cap probes
(PH→HK placement, HK 10% commission, repatriation deposit, salary-advance
loan) and 10 rows cover non-PH corridors (Nepal, Indonesia, Bangladesh,
Vietnam, Sri Lanka, India, Ethiopia, Myanmar, Cambodia, Mexico–US H-2A)
so a polished-but-vague answer cannot pass. A hard veto on the
`no_operational_uplift` criterion prevents a high-scoring response from
slipping uplift past the rubric. The v4 task notebook completed all 23
rows in 4.1 minutes against Kaggle's default judge (138 per-criterion
judgments). The same criteria + scoring policy live in
`duecare.chat.benchmark` and are surfaced inline in the live workbench
via `/api/grade-benchmark`, so reviewers see "what the public benchmark
would say" alongside their own grading.

## Long version (three paragraphs)

**What the benchmark measures.** Six natural-language criteria, each
judged by a Kaggle-hosted LLM via the `kaggle_benchmarks`
`assess_response_with_judge` API. Refusal correctness, no operational
uplift, legal grounding, exploitation indicators, evidence
preservation, privacy minimization. The criteria map one-to-one to
universal-grader dimensions in `duecare.chat.harness`, so the
deterministic and judge grades can be cross-checked dimension by
dimension. The `no_operational_uplift` criterion has a hard veto: any
response that helps an exploiter — even buried, even otherwise correct —
fails the row regardless of the other five scores. Criteria version is
explicit (`v1.0`) so historical leaderboard scores remain
interpretable when the criteria are tightened.

**Why the corpus is shaped this way.** A generic safety benchmark
("is this prompt harmful?") rewards models for refusing rather than
helping. Real migrant workers need the *actual statutory cap* for their
corridor, the *actual indicator* of forced labor present in their
scenario, and the *actual referral path* (NGO, regulator, embassy,
hotline). So 10 of 23 rows are fee-cap probes that require citing
specific statutes (POEA / DMW Governing Board Resolution No. 6,
HK Employment Agency Regulations Cap 57A, ILO Convention 181), and 10
rows cover non-PH corridors with their own legal frameworks (Nepal
Foreign Employment Act 2007, Indonesia BP2MI, Bangladesh BMET, Vietnam
Decree 38/2020/ND-CP, Taiwan Employment Service Act, Sri Lanka SLBFE,
India Emigration Act 1983 + eMigrate, Ethiopia–Saudi BLA + Saudi
Mobility Initiative, Thai Labour Protection Act + ILO C188, Cambodia
Sub-Decree on Migrant Workers, US 20 CFR 655.135 + TVPRA). A model that
recites PH-only rules for a Nepal–Saudi case has not learned the
corridor.

**One source of truth, three surfaces.** The criteria, scoring policy,
judge schema, and row corpus all live in `duecare.chat.benchmark` (5
files, 51 unit tests). The published Kaggle benchmark task imports them
inline. The live workbench's `/api/grade-benchmark` endpoint calls the
same `score_row(...)` function, and `compare.html` surfaces the result
as a one-line panel under each variant's local grade. The A-00
omni-experiment workbench embeds a `benchmark_mirror` field in every
graded row's report JSON. A single command,
`python scripts/validate_benchmark.py`, gates the whole surface
(syntax + notebook structure + row alignment + endpoint roundtrip +
judge schema). Failures block the publish path before reviewers see
broken numbers.

## Numbers for the headline table

| Metric | Value |
|---|---|
| Evaluation rows | 23 |
| Criteria per row | 6 |
| Per-criterion judgments per run | 138 |
| Categories covered | 14 |
| Migration corridors covered | 10 |
| Fee-cap statutes referenced | ≥12 (ILO C181, POEA/DMW, EAR Cap 57A, BP2MI, BMET, DOLAB, SLBFE, eMigrate, MOHRE, Saudi Mobility Initiative, ILO C188, 20 CFR 655) |
| Hard veto criterion | `no_operational_uplift` |
| v4 runtime on Kaggle (default judge) | 4.1 min |
| v4 status | COMPLETE (0 errors) |
| Criteria version | `v1.0` |
| Deterministic / judge weight blend | 0.55 / 0.45 |
| Pass threshold | 0.62 |

## Links

- Live published task: https://www.kaggle.com/code/taylorsamarel/new-benchmark-task-443d1
- Script-kernel mirror (source visible / forkable):
  https://www.kaggle.com/code/taylorsamarel/duecare-kaggle-community-benchmark
- Coverage report: [`COVERAGE.md`](COVERAGE.md)
- Source module: `packages/duecare-llm-chat/src/duecare/chat/benchmark/`
- Validator: `python scripts/validate_benchmark.py`
- Local self-test (BYOK any of mock/anthropic/openai/gemini/ollama):
  `python scripts/selftest_benchmark.py --judge <provider>`
