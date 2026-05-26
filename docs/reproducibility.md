# Reproducibility — every headline number, traced

> **Honest disclosure for judges.** This document grounds every
> quantitative claim in `docs/writeup_draft.md`,
> `docs/harness_lift_report.md`, `docs/readiness_dashboard.md`, and the
> video script. Each number has a provenance tuple
> `(git_sha, dataset_version, eval_set, grader_version, n)` and a
> one-command path to re-measure.
>
> **Most important caveat:** the headline lift numbers below were
> re-measured on May 25, 2026 from the current source with
> `python scripts/rubric_comparison.py`. Do not copy older +56.5pp /
> +87.5pp / +51.2pp / +34.1pp figures into new public materials.
> Re-run the command before making a fresh public claim.
>
> **Evidence maturity:** these are reproducible smoke / proxy
> measurements for regression tracking. They are not the result of a
> weeks-long local Gemma run, production traffic, or a field deployment.

## Headline numeric claims and their provenance

| Claim | Where cited | Last measured | Provenance |
|---|---|---|---|
| **+73.8 pp** Jurisdiction-specific rules | docs site + harness lift report | 2026-05-25 | `docs/harness_lift_data.json`, current 200+ prompt proxy eval set x `legal_citation_quality` 12-criterion rubric |
| **+55.4 pp** ILO / international regulations | docs site + harness lift report | 2026-05-25 | same |
| **+21.2 pp** Substance-over-form analysis | docs site + harness lift report | 2026-05-25 | same |
| **+51.4 pp** combined GREP+RAG (current headline) | docs site + harness lift report | 2026-05-25 | layer ablation: `legal_citation_quality` weighted average over the current 200+ prompt proxy eval set |
| **+46.9 pp** GREP only | harness lift report | 2026-05-25 | appendix B layer ablation |
| **+29.7 pp** RAG only | harness lift report | 2026-05-25 | appendix B layer ablation |
| Citation-shaped strings outside the allowlist in harness-ON proxy outputs | harness lift report | 2026-05-25 | appendix C citation-grounding scan; exact generated counts live in `docs/harness_lift_data.json`; review signal, not production defect rate |
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

## Current re-measurement notes

The current measurement compares harness-OFF proxy responses against
harness-ON proxy responses augmented with the active GREP and RAG
layers. It still uses the current 200+ prompt `legal_citation_quality`
evaluation set, but the active rule corpus has changed since the older
May 3 snapshot. The current numbers are therefore the only smoke /
proxy figures that should be used on the docs site and in new public
materials until a live Gemma run produces a dated artifact bundle.

The active CI guard uses conservative floors under the current
measurement: mean lift >= +50pp, jurisdiction-specific lift >= +70pp,
ILO/international lift >= +45pp, and substance-over-form lift >= +20pp.
If any floor fails, fix the harness or update the public claims with a
new dated measurement. Do not promote these floors into field,
production, or long-run reliability claims.

## How to re-measure

Use `kaggle/A-00-omni-experiment-workbench/kernel.py` and export the
resulting evidence bundle from `/kaggle/working/a00_outputs`. For a
fast smoke run, keep prompt and synthetic-row counts small. For
presentation-quality claims, use the largest prompt count that fits the
available runtime and GPU budget, then cite the exported report bundle
and Activity ZIP. For production-quality claims, run a medium-sized
Gemma variant that fits the target hardware for multiple hours or days,
save the prompts, model revision, seed/config, logs, outputs, and
grading artifacts, and then update this page with the exact evidence
path.

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

- **We do not claim the older +56.5 pp number still represents the
  current expanded rule set.** The current checked-in measurement is
  +51.4 pp mean lift.
- **We do not claim the universal rubric grader matches human
  graders perfectly.** It catches the failure modes the rubric was
  designed for; semantic equivalents the lexicon doesn't know
  pass through and are caught by the LLM-as-judge layer instead.
- **We do not claim the LLM-as-judge grader is unbiased.** It uses
  the same Gemma 4 model the response came from (self-consistency
  check, not external auditor). For external audit, swap in any
  cloud BYOK route via the model selector.
- **We do not claim production citation traceability yet.** The current
  harness-lift proxy found some citation-shaped strings outside the
  allowlist among the harness-ON citation-shaped strings. Treat the
  generated counts as a manual-review signal from a heuristic scan,
  not a production defect rate and not a weeks-long Gemma reliability
  measurement.

## Next evidence target

The next stronger claim should come from a long-running local Gemma
evaluation, not from this smoke gate. Minimum useful evidence:

1. Run a medium-sized Gemma variant that fits the available hardware
   for a multi-hour or multi-day benchmark.
2. Keep every prompt, model revision, seed/config, retrieved knowledge
   object, generated answer, grading output, and Activity ZIP.
3. Report citation grounding as an audited artifact: supported,
   unsupported, ambiguous, and manually reviewed.
4. Publish the dated artifact path before updating docs, press copy, or
   GitHub Pages headline metrics.

## Citation grounding scan

Citation-shaped strings in evaluated Gemma responses are checked by the
current heuristic and corpus scan. Treat this as an audited grounding artifact,
not as a production guarantee that every future answer will be fully cited:

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

Total citation-corpus size and supported/unsupported citation rates should be
read from the current corpus manifest, A-00 evidence bundle, or manual review
artifact rather than copied from this historical snapshot.

## Provenance for non-numeric claims

| Claim | Source / file |
|---|---|
| "no PII in the repo" | git history clean post `c07019c` purge; pre-commit hook + `.claude/rules/10_safety_gate.md` |
| "MIT license" | `LICENSE` file |
| "uses Gemma 4 variants" | Active Kaggle kernels: `kaggle/01-duecare-exploration-workbench/kernel.py` and `kaggle/02-live-demo/kernel.py`; re-check the variant map before naming an exact set. |
| "model selector" | Shared workbench chrome (`_nav.html`, `_nav.js`, `_chrome.css`) plus the active kernel variant map; do not publish an exact variant count without a current audit. |
| "harness toggles" | `harness/__init__.py:default_harness()`; cite runtime self-audit output for exact enabled layers. |
| "grading endpoints" | Chat package API routes for universal/expert/deep/combined grading; re-run route inventory before publishing an exact count. |
| "corridor lookup tables" | `harness/__init__.py:CORRIDOR_FEE_CAPS` + `OPF_CORRIDORS`; cite the current runtime inventory for exact corridor counts. |
| "NGO intake registry" | `harness/__init__.py:NGO_INTAKE`; cite the current runtime inventory for exact group counts. |

## Summary table (what to read in what order)

1. **`docs/writeup_draft.md`** — submission writeup with headline numbers (~1500 words)
2. **`docs/harness_lift_report.md`** — full lift methodology + per-prompt breakdowns
3. **`docs/reproducibility.md`** *(this file)* — provenance for every number
4. **`docs/peer_review_5min_test_plan.md`** — the judge entry point
5. **`docs/readiness_dashboard.md`** — current status and evidence-run targets
6. **`docs/architecture.md`** — technical design (20 sections)
7. **`docs/FOR_PEER_REVIEW.md`** — quick-orient overview
