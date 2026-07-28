<!--
ANNOTATED REPORT TEMPLATE - model-failure study.

Keep this file aligned with scripts/model_failure_report.py and
model_failure_study_methodology.md. The renderer supplies deterministic tables,
separate contextual-judge panels, and agreement. A human author adds the
executive interpretation and carefully selected appendix only after checking
coverage, missingness, privacy, and the claim boundary.
-->

# {{TITLE}}

> **Evidence status:** {{historical/current campaign}}, {{directional or
> per-dimension protocol}}, {{human ratings count}}. Automated judgments are
> not human validation or ground truth.

## 0. Run provenance

| Field | Value |
|---|---|
| Git revision | {{git_sha}} |
| Campaign manifest and hash | {{manifest}} / {{manifest_sha256}} |
| Candidate provider/model | {{provider}} / {{candidate_model}} |
| Candidate condition | {{baseline or harnessed}} |
| Prompt selection | {{count, seed, category count, selection hash}} |
| Context mode and hash | {{none/core/full}} / {{context_set_sha256}} |
| Deterministic rubric | {{rubric version/hash}} |
| Cross-family judge | {{model, provider, protocol, rubric hash}} |
| Same-family judge | {{model, provider, protocol, rubric hash}} |
| Temperature/output caps | {{settings}} |
| Budget receipt | {{run IDs, caps, sanitized receipt paths}} |
| Date | {{run_date}} |

Disclose missing, failed, truncated, ERROR, and UNPARSED rows. An access failure
is not a model score.

## 1. Executive summary

AUTHOR: lead with the best-supported finding on the frozen sample. Separate:

- recognition and safety;
- specific grounding and sense resolution;
- actionability;
- deterministic/judge agreement;
- cross-family/self-family agreement; and
- uncertainty requiring human adjudication.

Do not claim that a model endorses harm merely because a surface-form screen
returned FAIL. Do not call an automated panel definitive.

## 2. Deterministic screen

| Model | Did-not-resolve | Endorsed wrong sense | Incomplete | Resolved | Avg overall % |
|---|---|---|---|---|---|
| `{{model}}` | {{rate}} | {{rate}} | {{count}} | {{count}} | {{score}} |

Label this table as a reproducible conservative screen with known
surface-form/applicability noise.

## 3. Cross-family contextual automated judge

**Judge:** `{{judge_model}}`

**Protocol:** {{holistic directional OR one-call-per-dimension}}

**Relationship:** cross-family; eligible as primary automated evidence, not as
human validation.

| Model | sense_resolution | legal_grounding | harm_safety | actionability |
|---|---|---|---|---|
| `{{model}}` | {{pass/count}} | {{pass/count}} | {{pass/count}} | {{pass/count}} |

## 4. Same-family contextual self-judge

**Judge:** `{{judge_model}}`

**Protocol:** {{protocol}}

**Relationship:** self-family diagnostic; never blend this table into the
primary automated result.

| Model | sense_resolution | legal_grounding | harm_safety | actionability |
|---|---|---|---|---|
| `{{model}}` | {{pass/count}} | {{pass/count}} | {{pass/count}} | {{pass/count}} |

## 5. Agreement and disagreement

| Comparison | Exact agreement | Shared rows | Missing rows |
|---|---:|---:|---:|
| Deterministic vs cross-family `sense_resolution` | {{rate}} | {{n}} | {{n}} |
| Deterministic vs self-family `sense_resolution` | {{rate}} | {{n}} | {{n}} |
| Cross-family vs self-family, all dimensions | {{rate}} | {{n}} | {{n}} |

AUTHOR: stratify by category and identify the largest disagreements for blind
qualified human review. Preserve disagreement; do not average it away.

## 6. Per-prompt and category findings

| Prompt/category | Count | Deterministic result | Cross-family result | Self-family result |
|---|---:|---|---|---|
| `{{id}}` | {{n}} | {{summary}} | {{summary}} | {{summary}} |

## 7. Baseline versus harnessed lift

Include this only when a paired harness arm actually ran under the same frozen
selection and protocol.

| Model | Baseline | Harnessed | Delta | Paired coverage |
|---|---:|---:|---:|---:|
| `{{model}}` | {{score}} | {{score}} | {{delta}} | {{n}} |

If it did not run, say so directly. Do not imply lift from a candidate-only
campaign.

## 8. Method, limitations, and claim boundary

State prompt selection, context construction, deterministic rubric, judge
protocol, relationship controls, budget, resume behavior, privacy boundary,
model/version drift, synthetic-sample limits, and absent human evidence.

## 9. Appendix

AUTHOR: select examples using a declared rule (for example highest-confidence
agreement, largest disagreement, and one benign control), not because they
support the preferred headline. Publish full text only after privacy and rights
review; otherwise publish hashes, metadata, and bounded excerpts.

---

Render candidate and both judge files with:

```powershell
python scripts/model_failure_report.py `
  --in <candidate-results.jsonl> `
  --judge <cross-family-judge.jsonl> <self-family-judge.jsonl> `
  --out <report.md>
```
