# Deterministic full-registry verification -- gemma4:31b

Model-free `duecare.kit.verify` scored on every generated (baseline,
harness_core) response pair. No judge model, no network -- fully reproducible.

- paired prompts scored: **78,719**
- deterministic mean score: baseline **3.966/5** -> harness_core **4.828/5** (**+0.861** lift)
- score regressions (harness_core < baseline): **2,196** (2.79%)

## Per-criterion regressions (baseline passed, harness failed)

| criterion | meaning | regressions |
|---|---|---|
| A | indicator surfaced | 401 |
| B | legal citation | 4 |
| C | refusal + redirect | 449 |
| D | resource routing | 2,275 |
| E | privacy clean | 0 |

Privacy (E) never regresses; legal grounding (B) almost never does. The single
meaningful weak spot is D (resource routing) -- diagnosed in
`docs/research/harness_hurts_review_2026_07_21.md` as mostly an ordering/prominence
issue (the harness demotes a concrete resource under its analytical preamble),
not lost content.

CSV: `docs/external_review/deterministic_verify_gemma4_31b.csv` (78,719 rows).
Regenerate: `python scripts/deterministic_full_registry.py --model gemma4:31b`.
