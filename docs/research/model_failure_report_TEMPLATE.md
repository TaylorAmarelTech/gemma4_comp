<!--
ANNOTATED REPORT TEMPLATE — model-failure study.

This is the canonical SHAPE of the final report. `scripts/model_failure_report.py`
auto-renders sections 2-6 from the result + judge JSONL; the human author writes
section 0 (executive summary) and section 7 (appendix selection). `{{...}}` marks
an auto-filled value; "AUTHOR:" marks prose a human writes after reading the data.

Keep this file in sync with `model_failure_report.py` (the renderer) and
`model_failure_study_methodology.md` (the spec). When the renderer changes a
section, update this template in the same commit.
-->

# {{TITLE}}  — e.g. "How frontier models handle human-exploitation prompts (baseline)"

> AUTHOR (1 paragraph, written LAST, after reading the judge table). Lead with the
> honest headline, which is **RQ2 (grounding)**, NOT an over-claimed "models endorse
> exploitation". Template sentence:
> *"Across {{n_models}} models and {{n_probes}} equivocation probes, models almost
> always recognised the exploitation framing as problematic ({{harm_safety_pass}}%
> harm-safety PASS) but {{legal_grounding_pass}}% grounded the answer in the specific
> instrument (ILO C029/C189, recruitment-fee rules, kafala) — and {{sense_pass}}%
> resolved the ambiguous term to its trafficking sense. That grounding gap is the
> measurable space the DueCare harness fills."*

## 0. Run provenance (reproducibility header)

| Field | Value |
|---|---|
| git_sha | {{git_sha}} |
| Provider / endpoint | {{provider}} ({{base_url}}) |
| Generation models | {{gen_models}} |
| Judge model | {{judge_model}} (independent; one dimension per call) |
| Prompt set | {{n_probes}} equivocation probes{{ + N seed prompts}} |
| Responses graded | {{n_responses}} ({{n_models}} models) |
| Temperature | 0 (generation + judging) |
| Date | {{run_date}} |

> AUTHOR note: state the judge-model **family** vs the tested-model families
> (bias control). If the judge family overlaps any tested model, disclose the
> self-judged rows.

## 1. Read this before the tables (caveat block — AUTO + AUTHOR)

- The dominant outcome is **PARTIAL** (recognise-but-don't-ground), not FAIL.
- The deterministic keyword screen is a **screen, not a verdict** — it false-FAILs a
  response that merely *quotes* a euphemism to debunk it. The **independent LLM judge
  (§3) is the definitive measure.**

## 2. Per-model — deterministic screen (AUTO from results JSONL)

| Model | Did-not-resolve | Endorsed wrong sense | Incomplete | Resolved | Avg overall % |
|---|---|---|---|---|---|
| `{{model}}` | {{equivocation_rate}} ({{n}}/{{applicable}}) | {{endorse_rate}} ({{n}}) | {{n_partial}} | {{n_resolved}}/{{applicable}} | {{avg_pct}} |

> Labelled a SCREEN. Worst overall first.

## 3. Independent LLM-judge verdicts (DEFINITIVE — AUTO from judge JSONL)

Each response re-graded by **`{{judge_model}}`**, one dimension per call. Cells show
the **PASS rate** per dimension.

| Model | sense_resolution | legal_grounding | harm_safety | actionability |
|---|---|---|---|---|
| `{{model}}` | {{pass_rate}} ({{PASS}}/{{n}}) | {{pass_rate}} | {{pass_rate}} | {{pass_rate}} |

> This is the credible verdict. The four dimensions map to the four research
> questions: harm_safety↔RQ1 (recognition), legal_grounding↔RQ2 (grounding),
> sense_resolution↔RQ3 (equivocation resistance), actionability↔safe next step.

## 4. Per-probe — hardest first (AUTO)

| Probe | Ambiguous term | Models equivocated |
|---|---|---|
| `{{prompt_id}}` | {{term}} | {{n}}/{{models}} ({{rate}}) |

## 5. Baseline vs DueCare-harnessed lift (AUTO when arm B present; else "not run")

| Model | Baseline grounding PASS | Harnessed grounding PASS | Δ |
|---|---|---|---|
| `{{model}}` | {{base}} | {{harnessed}} | **{{delta}}** |

> AUTHOR: this is the product claim — the harness's job is to convert PARTIAL
> (recognise) into PASS (ground + act). Quantify the conversion. If arm B was not
> run, state "harnessed arm deferred to <date>" — do NOT leave it implied.

## 6. Method + limitations (AUTO summary + AUTHOR limitations)

- Prompts, generation (neutral system msg, temp 0, no harness), two-layer grading.
- Limitations to STATE: deterministic grader keyword-noise; judge self-preference
  bias (mitigated by cross-family judge — name it); model-version drift (pin+date);
  provider concurrency differences normalised by the judge.

## 7. Appendix — representative responses (AUTHOR selects, AUTO quotes verbatim)

For each of {{k}} illustrative probes, the full prompt + full response (NO
truncation, per project rules) + the per-dimension judge verdict + one-line reason.
Choose: 1 best "resolved" example, 1 typical "recognise-but-don't-ground" PARTIAL,
1 worst (endorsed) if any, 1 equivocation-laundering attempt.

---
_Sections 2-6 auto-render via `scripts/model_failure_report.py --in <results> --judge <judge>`._
_Sections 0/1/7 are author-written after reading the rendered tables._
