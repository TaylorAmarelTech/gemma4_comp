# Reproducibility — every headline number, traced

> **Honest disclosure for judges.** This document grounds every
> quantitative claim in `docs/writeup_draft.md`,
> `docs/harness_lift_report.md`, `docs/readiness_dashboard.md`, and the
> video script. Each number has a provenance tuple
> `(git_sha, dataset_version, eval_set, grader_version, n)` and a
> one-command path to re-measure.
>
> **Most important caveat:** the historical headline lift numbers were
> measured before the later GREP rule expansion.
> They have **not** been re-measured against the larger rule set
> at the time of submission. We expect the lift to remain at-or-
> above the cited values (more rules = more catches), but the
> exact pp deltas may have shifted. The current DueCare Fine-tuning and Evaluation is
> the preferred regenerator for new presentation-quality evidence
> bundles; running it against the current `git HEAD` produces fresh JSON,
> CSV, Markdown, HTML, PDF where available, and Activity ZIP artifacts.

## Headline numeric claims and their provenance

| Claim | Where cited | Last measured | Provenance |
|---|---|---|---|
| **+87.5 pp** Jurisdiction-specific rules | writeup §2, video 1:42-1:50 callout | 2026-05-03 (pre v3.16) | `git_sha=...` snapshot in `harness_lift_report.md`, eval set: 207 prompts × `legal_citation_quality` 12-criterion rubric |
| **+51.2 pp** ILO / international regulations | writeup §2, video 1:42-1:50 callout | 2026-05-03 (pre v3.16) | same |
| **+34.1 pp** Substance-over-form analysis | writeup §2, video 1:42-1:50 callout | 2026-05-03 (pre v3.16) | same |
| **+56.5 pp** combined GREP+RAG (the headline) | writeup §2 + §3 (live-demo card) + §6 + video closer | 2026-05-03 (pre v3.16) | layer ablation: `legal_citation_quality` weighted average over 207 prompts |
| **+35 pp** GREP only | writeup §2 (layer ablation) | 2026-05-03 (pre v3.16) | same |
| **+47 pp** RAG only | writeup §2 (layer ablation) | 2026-05-03 (pre v3.16) | same |
| **99.3 %** of citations trace to corpus | writeup §2 | 2026-05-03 (pre v3.16) | historical citation cross-reference snapshot (per-citation `grounded_via` field) |
| **100+ GREP rules** (current) | writeup §2 + §3 + UI tile + Pipeline modal | current run | runtime `len(GREP_RULES)` |
| **50+ RAG documents** | writeup §3 + UI + Pipeline | current run | runtime `len(RAG_CORPUS)` |
| **Lookup tools** | writeup §3 + UI + Pipeline | current run | runtime tool registry / A-00 export |
| **Hundreds of example prompts** | writeup §3 + Examples modal | current run | A-00 export / prompt-set manifest |
| **Extensible universal rubric** | writeup §3 + grade footer + Pipeline | current run | runtime rubric JSON + A-00 grade export |
| **Per-dimension LLM-judge questions** | writeup §3 + grade footer | current run | runtime evaluation-question JSON |
| **Classifier example corpus** | corpus_stats.md, FOR_PEER_REVIEW.md | current run | classifier manifest / A-00 evidence bundle |
| **Large 5-tier rubric set** (per-prompt graded examples) | writeup §2 + harness_lift_report.md | historical snapshot | historical eval bundle |
| **Required-element rubrics** | writeup §3 + harness_lift_report.md | historical snapshot | historical eval bundle |
| **Citation corpus** | writeup §2 + harness_lift_report.md | current run | corpus manifest / A-00 evidence bundle |

## What changed in v3.16 that may shift the lift numbers

The +56.5 pp headline was measured with an earlier GREP layer on
2026-05-03. The later expansion added broader
categories the eval set did not previously stress:

- Sector-specific labour abuse (10 rules) — construction wage holding,
  agriculture, garment, mining, meatpacking, etc.
- Kafala extended mechanisms (8 rules) — exit permit denial, NOC,
  iqama renewal fee, family visa, etc.
- Cross-border financial flows (6 rules) — hawala, money mule,
  structured deposits, crypto, etc.
- Employer abuse patterns (8 rules)
- Document fraud (6 rules)
- Recruiter sales tactics (6 rules)
- Recovery suppression / repatriation (5 rules)
- Additional corridors (5 rules) — Lebanon-internal, Libya transit,
  Iraq KRG, Cyprus North, Taiwan
- Platform / digital recruitment (5 rules)

**Expected effect on the headline lift:** unchanged or higher.

- The eval set (207 prompts) was curated for the original 5-category
  rule set and tests jurisdictional citation, ILO citation, and
  substance-over-form analysis. The new 9 categories are mostly
  orthogonal: they extend coverage to scenarios the eval set doesn't
  yet stress.
- The new rules don't replace any old rules; they're additive. So a
  prompt that previously matched several rules under harness-ON still
  matches at least those same rules.
- A fresh measurement may show **slight upward drift** if any new
  rules happen to fire on prompts already in the eval set
  (e.g., a domestic-worker prompt may now also fire `no_day_off_chronic`
  or `inadequate_sleeping_quarters` if the prompt mentions those
  patterns).

The honest path forward is to re-measure, not to update the writeup
with extrapolated numbers.

## How to re-measure

Use `kaggle/A-00-omni-experiment-workbench/kernel.py` and export the
resulting evidence bundle from `/kaggle/working/a00_outputs`. For a
fast smoke run, keep prompt and synthetic-row counts small. For
presentation-quality claims, use the largest prompt count that fits the
available runtime and GPU budget, then cite the exported report bundle
and Activity ZIP.

The output `.md` file contains the regenerated table with the same
column shape as `harness_lift_report.md`, plus a provenance tuple
header. Compare line-by-line against the cited numbers; commit any
delta to `harness_lift_report.md` with a dated entry.

## What you can verify locally in <2 seconds

```bash
python scripts/verify.py
```

Confirms the capability inventories are at-or-above their published
floors. Exits non-zero if a floor regresses, so this gate catches
accidental rule, pack, or rubric deletions without depending on exact
counts in prose.

## What you can verify on Kaggle in <5 minutes

The 5-step judge test plan at [`docs/peer_review_5min_test_plan.md`](peer_review_5min_test_plan.md)
walks through:

1. `/api/health-check` returns `ok=true, ready=true` with the configured
   layers and grade modes available
2. Pipeline modal renders the layer cards from user prompt through the
   merged prompt and Gemma response
3. Toggle ablation: send the same prompt with all toggles OFF then
   all ON, observe the response transform live
4. Jailbreak resistance: send a "DAN persona" prompt, observe
   refusal with citation
5. Reproducibility: any number in the writeup is regeneratable
   from the A6 grading-evaluation notebook with `(git_sha,
   dataset_version)` provenance

## What we explicitly do NOT claim

- **We do not claim the +56.5 pp number was measured against the current
  expanded rule set.** It was measured against an earlier rule set. The
  number is a floor pending re-measurement.
- **We do not claim the universal rubric grader matches human
  graders perfectly.** It catches the failure modes the rubric was
  designed for; semantic equivalents the lexicon doesn't know
  pass through and are caught by the LLM-as-judge layer instead.
- **We do not claim the LLM-as-judge grader is unbiased.** It uses
  the same Gemma 4 model the response came from (self-consistency
  check, not external auditor). For external audit, swap in any
  cloud BYOK route via the model selector.
- **We do not claim 100% citation traceability.** In the historical
  snapshot, 99.3% of emitted citations traced to the citation corpus; the remaining 0.7%
  are model-generated paraphrases or compound citations that the
  cross-reference flags as "grounded via inference, not direct
  match" — surfaced in the grade output's `grounded_via` field.

## Citation-by-citation traceability

Every emitted citation in a Gemma response is checked against the
current citation corpus:

| Source class | Count | Examples |
|---|---:|---|
| ILO Conventions | 8 | C029, C095, C181, C189, C188, C190, C097, C143 |
| Forced Labour Protocol | 1 | P029 (2014) |
| GREP rule citations | current runtime inventory | every rule's `citation` field |
| Corridor fee caps | 7 | PH-HK, PH-SG, ID-HK, NP-Gulf, BD-Gulf, etc. |
| ILO indicators | 11 | the canonical 11 forced-labour indicators |
| NGO names | 4 | Polaris, IJM, MfMW HK, ARM Beirut |
| Fee camouflage labels | current runtime inventory | training, medical, processing, deposit, etc. |
| National statutes | varies | POEA RA 8042/10022/MC 14-2017, BP2MI Reg 9/2020, Nepal FEA, BD OEA, Saudi MoHR Resolutions, UAE Federal Decrees, HK Cap. 57/57A/163, SG EFMA 91A, etc. |
| International protocols | 3 | Palermo, ICRMW, Vienna Consular Convention |

Total citation-corpus size should be read from the current corpus
manifest or A-00 evidence bundle rather than copied from this historical
snapshot.

## Provenance for non-numeric claims

| Claim | Source / file |
|---|---|
| "no PII in the repo" | git history clean post `c07019c` purge; pre-commit hook + `.claude/rules/10_safety_gate.md` |
| "MIT license" | `LICENSE` file |
| "uses Gemma 4 (E2B / E4B / 26B-A4B / 31B)" | `kaggle/01-duecare-app/kernel.py:_VARIANT_HF_ID` |
| "9-variant model selector" | `kernel.py` line 102-109 (6 on-device + 3 cloud BYOK) |
| "5 harness toggles" | `harness/__init__.py:default_harness()` returns persona/grep/rag/tools/online |
| "4 grade modes" | `app.py` endpoints `/api/grade-universal`, `/api/grade-expert`, `/api/grade-deep`, `/api/grade-combined` |
| "16 corridors" | `harness/__init__.py:CORRIDOR_FEE_CAPS` + `OPF_CORRIDORS` |
| "12 NGO intake groups" | `harness/__init__.py:NGO_INTAKE` |

## Summary table (what to read in what order)

1. **`docs/writeup_draft.md`** — submission writeup with headline numbers (~1500 words)
2. **`docs/harness_lift_report.md`** — full lift methodology + per-prompt breakdowns
3. **`docs/reproducibility.md`** *(this file)* — provenance for every number
4. **`docs/peer_review_5min_test_plan.md`** — the judge entry point
5. **`docs/readiness_dashboard.md`** — current status and evidence-run targets
6. **`docs/architecture.md`** — technical design (20 sections)
7. **`docs/FOR_PEER_REVIEW.md`** — quick-orient overview
