# Duecare Eval — rubrics + benchmarks + regression gate

**Status: Partial.** Rubric + adversarial suite + LLM-judge mode
shipped. CI regression gate is post-hackathon.

The research and quality-control layer. Eval **gates** changes from
the continuous update system: Sentinel proposes; Eval decides if the
proposal is safe enough to ship.

## Built today

| Submodule | Status | Where |
|---|---|---|
| Universal rubric | **Built** | `harness/_rubric_universal.json` |
| Domain-specific rubrics | partial — trafficking only; tax_evasion / financial_crime stubbed | `_governance.py` |
| Evaluation questions (LLM-judge templates) | **Built** | `harness/_evaluation_questions.json` |
| Adversarial suite | **Built** | `scripts/adversarial_validate.py` |
| Model comparison (stock vs harnessed, OFF/ON ablation) | **Built** | A/B Compare tab + `▸ Run ablation` button |
| Regression tests | **Partial** | sanitizer regression suite at `tests/test_model_output.py`; full gate post-hackathon |
| Benchmark notebooks | **Built** | `kaggle/A-00-omni-experiment-workbench/` combined judging and report path |
| Governance checks (validate every domain-pack release) | **Built** (curator block) / **Pending** (full gate) | `scripts/validate_curator_blocks.py` |

## Four grade modes

1. **Universal** (deterministic, ~2s) — multi-signal scoring across
   current rubric dimensions; checks keyword + cluster + token-overlap
   against `pass_indicators` / `fail_indicators` arrays.
2. **Expert** (legacy per-category) — for backwards compatibility.
3. **Evaluator** (LLM-as-judge, ~30-90s) — sends response back to
   the loaded Gemma with one focused yes/no question per applicable
   dimension; pulls evidence quotes from the response itself.
4. **Combined** (Universal + Evaluator, blended 50/50) — disagreement
   panel surfaces the high-information dimensions where the two
   graders see different evidence.

## Citation grounding check

Every cited statute / convention / hotline in the response is
checked against a curated allowlist (~210 reference points across
RAG / GREP / corridor / ILO indicator / NGO / fee-camouflage
catalogs). Hallucinated quotes are demoted to PARTIAL.

## Section verification

`§4(c)`, `§32`, `§17` references are checked against
`_known_statute_sections.json` to catch "RA 8042 §99" hallucinations.

## Baseline gauge

`_baseline_gauge.json` ships with honest disclosure: stock 6% /
harnessed 88% measured against v3.5 rubric (19 dims); v3.10
current-rubric re-measurement is pending GPU budget. Live grader uses
the current rubric. The gauge is labeled with its rubric version so
users don't mistake it for a current measurement.

## Reproducibility tuple

Every grade carries `(model_revision, git_sha, dataset_version)`.
The "+56.5pp" headline regenerates live via the active evaluation
path or via a single-button `▸ Run ablation` in
the chat UI (4 generations OFF / GREP / RAG / BOTH).

## Roadmap

- **Full CI regression gate** — every curator-block PR runs the
  adversarial suite + benchmark eval set; blocks merge if pass-rate
  drops more than threshold.
- **Domain rubric expansion** — explicit tax_evasion +
  financial_crime + child_protection rubrics with their own
  evaluator-question packs.
- **Cross-model comparison harness** — Gemma 4 vs other open
  models on the same rubric; today only Gemma 4 + cloud
  fallbacks are wired.
