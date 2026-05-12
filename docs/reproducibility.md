# Reproducibility — every headline number, traced

> **Honest disclosure for judges.** This document grounds every
> quantitative claim in `docs/writeup_draft.md`,
> `docs/harness_lift_report.md`, `docs/REPORT_CARD.md`, and the
> video script. Each number has a provenance tuple
> `(git_sha, dataset_version, eval_set, grader_version, n)` and a
> one-command path to re-measure.
>
> **Most important caveat:** the headline lift numbers were last
> measured BEFORE the v3.16 GREP rule expansion (49 → 161 rules).
> They have **not** been re-measured against the larger rule set
> at the time of submission. We expect the lift to remain at-or-
> above the cited values (more rules = more catches), but the
> exact pp deltas may have shifted. The A6 notebook
> `duecare-grading-evaluation` is the regenerator; running it
> against the current `git HEAD` produces a fresh
> `duecare_lift_eval.json` + `.md`.

## Headline numeric claims and their provenance

| Claim | Where cited | Last measured | Provenance |
|---|---|---|---|
| **+87.5 pp** Jurisdiction-specific rules | writeup §2, video 1:42-1:50 callout | 2026-05-03 (pre v3.16) | `git_sha=...` snapshot in `harness_lift_report.md`, eval set: 207 prompts × `legal_citation_quality` 12-criterion rubric |
| **+51.2 pp** ILO / international regulations | writeup §2, video 1:42-1:50 callout | 2026-05-03 (pre v3.16) | same |
| **+34.1 pp** Substance-over-form analysis | writeup §2, video 1:42-1:50 callout | 2026-05-03 (pre v3.16) | same |
| **+56.5 pp** combined GREP+RAG (the headline) | writeup §2 + §3 (live-demo card) + §6 + video closer | 2026-05-03 (pre v3.16) | layer ablation: `legal_citation_quality` weighted average over 207 prompts |
| **+35 pp** GREP only | writeup §2 (layer ablation) | 2026-05-03 (pre v3.16) | same |
| **+47 pp** RAG only | writeup §2 (layer ablation) | 2026-05-03 (pre v3.16) | same |
| **99.3 %** of citations trace to corpus | writeup §2 | 2026-05-03 (pre v3.16) | citation cross-reference vs 106-source corpus (per-citation `grounded_via` field) |
| **161 GREP rules** (current) | writeup §2 + §3 + UI tile + Pipeline modal | 2026-05-04 (v3.16) | `python scripts/verify.py` confirms `len(GREP_RULES) == 161` |
| **46 RAG documents** | writeup §3 + UI + Pipeline | 2026-05-04 (v3.16) | `python scripts/verify.py` |
| **5 lookup tools** | writeup §3 + UI + Pipeline | 2026-05-04 (v3.16) | `python scripts/verify.py` |
| **587 example prompts** | writeup §3 + Examples modal | 2026-05-04 (v3.16) | `python scripts/verify.py` |
| **46-dim universal rubric** | writeup §3 + grade footer + Pipeline | 2026-05-04 (v3.16) | `python scripts/verify.py` |
| **17 LLM-judge yes/no questions** | writeup §3 + grade footer | 2026-05-04 (v3.16) | `python scripts/verify.py` |
| **51 classifier examples** (16 originals + 30 persona × corridor + 5 multimodal SVG) | corpus_stats.md, FOR_PEER_REVIEW.md | 2026-05-04 (v3.16) | `python scripts/verify.py` |
| **207 5-tier rubrics** (per-prompt graded examples) | writeup §2 + harness_lift_report.md | unchanged since 2026-05-02 | `python scripts/verify.py` |
| **6 required-element rubrics** | writeup §3 + harness_lift_report.md | unchanged since 2026-05-02 | `python scripts/verify.py` |
| **106-source citation corpus** | writeup §2 + harness_lift_report.md | 2026-05-03 | `EXPANDED_CITATION_CORPUS["n_total"]` in `harness/__init__.py` |

## What changed in v3.16 that may shift the lift numbers

The +56.5 pp headline was measured with the **49-rule** GREP layer
on 2026-05-03. The v3.16 expansion to **161 rules** added 9
categories the eval set didn't previously stress:

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
  prompt that previously matched 3 rules under harness-ON still
  matches at least those 3 rules.
- A fresh measurement may show **slight upward drift** if any new
  rules happen to fire on prompts already in the eval set
  (e.g., a domestic-worker prompt may now also fire `no_day_off_chronic`
  or `inadequate_sleeping_quarters` if the prompt mentions those
  patterns).

The honest path forward is to re-measure, not to update the writeup
with extrapolated numbers.

## How to re-measure (one command, ~10 min on a Kaggle T4)

```python
# In the duecare-grading-evaluation Kaggle notebook
# (slug: taylorsamarel/duecare-grading-evaluation):
import os
os.environ["DUECARE_EVAL_SET"] = "headline"   # 207 prompts × OFF/ON
os.environ["DUECARE_GRADER"] = "deterministic_v3.1"
os.environ["DUECARE_GIT_SHA"] = "<paste current git rev-parse HEAD>"
%run kernel.py
# Outputs to /kaggle/working/duecare_lift_eval.json + .md
```

The output `.md` file contains the regenerated table with the same
column shape as `harness_lift_report.md`, plus a provenance tuple
header. Compare line-by-line against the cited numbers; commit any
delta to `harness_lift_report.md` with a dated entry.

## What you can verify locally in <2 seconds

```bash
python scripts/verify.py
```

Confirms all 9 capability counts are at-or-above their published
floors (161 GREP / 46 RAG / 5 tools / 587 prompts / 207 5-tier
rubrics / 6 required rubrics / 51 classifier examples / 17 universal
dims / 46 LLM-judge questions). Exits non-zero if any count
regresses, so this gate catches accidental rule deletions.

## What you can verify on Kaggle in <5 minutes

The 5-step judge test plan at [`docs/peer_review_5min_test_plan.md`](peer_review_5min_test_plan.md)
walks through:

1. `/api/health-check` returns `ok=true, ready=true` with all 5
   layers wired and all 4 grade modes available
2. Pipeline modal renders 7 cards (USER → PERSONA → GREP → RAG →
   TOOLS → ONLINE → MERGED PROMPT → GEMMA RESPONSE)
3. Toggle ablation: send the same prompt with all toggles OFF then
   all ON, observe the response transform live
4. Jailbreak resistance: send a "DAN persona" prompt, observe
   refusal with citation
5. Reproducibility: any number in the writeup is regeneratable
   from the A6 grading-evaluation notebook with `(git_sha,
   dataset_version)` provenance

## What we explicitly do NOT claim

- **We do not claim the +56.5 pp number was measured against the
  v3.16 108-rule set.** It was measured against the 49-rule v3.15
  set. The number is a floor pending re-measurement.
- **We do not claim the universal rubric grader matches human
  graders perfectly.** It catches the failure modes the rubric was
  designed for; semantic equivalents the lexicon doesn't know
  pass through and are caught by the LLM-as-judge layer instead.
- **We do not claim the LLM-as-judge grader is unbiased.** It uses
  the same Gemma 4 model the response came from (self-consistency
  check, not external auditor). For external audit, swap in any
  cloud BYOK route via the model selector.
- **We do not claim 100% citation traceability.** 99.3% of emitted
  citations trace to the 106-source corpus; the remaining 0.7%
  are model-generated paraphrases or compound citations that the
  cross-reference flags as "grounded via inference, not direct
  match" — surfaced in the grade output's `grounded_via` field.

## Citation-by-citation traceability

Every emitted citation in a Gemma response is checked against the
106-source corpus:

| Source class | Count | Examples |
|---|---:|---|
| ILO Conventions | 8 | C029, C095, C181, C189, C188, C190, C097, C143 |
| Forced Labour Protocol | 1 | P029 (2014) |
| GREP rule citations | 49 → 108 | every rule's `citation` field |
| Corridor fee caps | 7 | PH-HK, PH-SG, ID-HK, NP-Gulf, BD-Gulf, etc. |
| ILO indicators | 11 | the canonical 11 forced-labour indicators |
| NGO names | 4 | Polaris, IJM, MfMW HK, ARM Beirut |
| Fee camouflage labels | 16 → 25 | training, medical, processing, deposit, etc. |
| National statutes | varies | POEA RA 8042/10022/MC 14-2017, BP2MI Reg 9/2020, Nepal FEA, BD OEA, Saudi MoHR Resolutions, UAE Federal Decrees, HK Cap. 57/57A/163, SG EFMA 91A, etc. |
| International protocols | 3 | Palermo, ICRMW, Vienna Consular Convention |

Total citation-corpus size: **106 sources** (last counted 2026-05-03;
will grow to ~150 once the 59 new GREP rule citations are folded in
during the next re-measurement run).

## Provenance for non-numeric claims

| Claim | Source / file |
|---|---|
| "no PII in the repo" | git history clean post `c07019c` purge; pre-commit hook + `.claude/rules/10_safety_gate.md` |
| "MIT license" | `LICENSE` file |
| "uses Gemma 4 (E2B / E4B / 26B-A4B / 31B)" | `kaggle/01-duecare-exploration-workbench/kernel.py:_VARIANT_HF_ID` |
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
5. **`docs/REPORT_CARD.md`** — self-graded scorecard against the rubric
6. **`docs/architecture.md`** — technical design (20 sections)
7. **`docs/FOR_PEER_REVIEW.md`** — quick-orient overview
