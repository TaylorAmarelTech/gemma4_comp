# Maintaining the GREP rule set

> The GREP layer is 161 regex KB rules across 16 categories. Each
> rule has a citation, severity, ILO indicator tag, and match-excerpt
> annotation. This guide explains how to add new rules, update
> existing ones, and handle the "the law amended; my rule is stale"
> case.

## Where the rules live

```
packages/duecare-llm-chat/src/duecare/chat/harness/__init__.py
↓
GREP_RULES = [
    {
        "rule":         "debt_bondage_with_passport_retention",
        "pattern":      r"(?i)passport.*(?:retention|withh|kept|seized).*debt",
        "citation":     "ILO C029 §2 + ILO Indicator 4 + Indicator 8",
        "severity":     "critical",
        "ilo_indicator": ["debt_bondage", "withholding_documents"],
        "category":     "debt_bondage",
        "notes":        "..."
    },
    ...
]
```

**Status:** Currently still inline Python (not migrated to curator
JSON yet — a v3.7 task). For now, GREP edits go via Python PR.

## Categories (16)

The 161 rules group by category (each ≈4-12 rules):

1. `debt_bondage` — interest >40%, retroactive consolidation
2. `fee_camouflage` — training/medical/processing/deposit relabeled fees
3. `corridor_caps` — PH→HK zero-fee, ID→HK BP2MI Reg 9/2020, etc.
4. `ilo_indicators` — direct mentions of the 11 indicators
5. `kafala_extended` — exit permits, NOC, sponsor transfer, huroob threats
6. `sectors` — domestic, fishing, construction, agriculture, garments
7. `cross_border_finflows` — novation laundering, multi-party stripping
8. `employer_abuse` — hours, breaks, food/water deprivation, isolation
9. `doc_fraud` — fake licenses, forged contracts, altered receipts
10. `recruiter_sales_tactics` — guarantee language, urgency pressure
11. `recovery_suppression` — repatriation barriers, complaint dismissals
12. `additional_corridors` — beyond the headline 16 (Lebanon, Syria, etc.)
13. `digital_recruitment` — TikTok/Facebook recruitment patterns
14. `multi_party` — sub-agent layering, governed-by stripping
15. `policy_evasion` — "as long as labeled X" patterns
16. `meta` — composite multi-rule indicators

## When to add a GREP rule

Good triggers:

- **A specific exploitation pattern keeps slipping past the existing
  rules.** Example: "free visa free ticket" — was added to the
  debt-bondage category in v3.16 to catch the Nepal-Gulf cabinet-
  decision-superseded pattern.
- **A new corridor + statute combination emerges.** Example:
  Lebanon Cabinet Decree 13166/2021 superseded the kafala system
  for domestic workers; needed dedicated rules.
- **A jailbreak pattern works in adversarial testing.** Add a rule
  that catches the operator-framing token ("as a recruiter, how do
  I optimize...") so the harness fires + the persona refuses.

Bad triggers:

- "The model didn't cite this convention." → Add the convention to
  RAG, not GREP. RAG is for retrieval; GREP is for trigger detection.
- "I want this single phrase recognized." → If it's a single
  phrase, it should be a classifier signal (curator JSON) not a
  GREP rule.

## Rule format

```python
{
    # 1. Stable id — used in the harness_trace + tests
    "rule":     "debt_bondage_with_passport_retention",

    # 2. Compiled regex (case-insensitive recommended)
    "pattern":  r"(?i)passport.*(?:retention|withh|kept|seized).*debt",

    # 3. Citation — the statute or instrument that justifies flagging this
    "citation": "ILO C029 §2 + ILO Indicator 4 + Indicator 8",

    # 4. Severity — affects how prominently it shows in the harness panel
    "severity": "critical",  # critical | high | medium | low

    # 5. ILO indicator tag(s) — for cross-referencing with the 11 indicators
    "ilo_indicator": ["debt_bondage", "withholding_documents"],

    # 6. Category — see the 16 categories above
    "category": "debt_bondage",

    # 7. Optional: notes for reviewers
    "notes":    "Catches the 'passport held until debt is paid' phrasing"
}
```

## Severity scale

- **critical** — the response MUST refuse + cite the prohibition.
  Example: passport retention, debt bondage with explicit threats.
- **high** — strong signal of trafficking; the response should refuse
  by default but with grounded explanation.
- **medium** — concerning but ambiguous; the response should ask
  clarifying questions OR refuse with caveats.
- **low** — useful informational signal but not necessarily
  exploitation. Example: a corridor mention without other red flags.

## Adding a rule (workflow)

1. **Verify the pattern doesn't already exist.** Grep:
   ```bash
   grep -A 3 "rule.*your_id" packages/duecare-llm-chat/src/duecare/chat/harness/__init__.py
   ```

2. **Test the regex** against representative inputs:
   ```bash
   python -c '
   import re
   pat = r"(?i)passport.*(?:retention|withh|kept).*debt"
   tests = [
       "they took my passport. i still owe debt",
       "my employer keeps my passport until I pay back the debt",
       "my passport is in the safe — no debt issues here",  # should NOT match
   ]
   for t in tests:
       print(bool(re.search(pat, t)), "—", t)
   '
   ```

3. **Add the rule** to `GREP_RULES`. Append to the right category
   block; preserve sorted order within the category.

4. **Add a test** in `test_harness_behavior.py`:
   ```python
   def test_grep_fires_on_passport_with_debt() -> None:
       h = _load_harness()
       result = h._grep_call("they took my passport. i still owe debt")
       rule_ids = {hit["rule"] for hit in result["hits"]}
       assert "debt_bondage_with_passport_retention" in rule_ids
   ```

5. **Run `python scripts/verify.py`** — confirms the count is at
   or above the published threshold (108).

6. **PR** with:
   - One-line summary: "Add GREP rule for X"
   - Cited statute or instrument
   - 2-3 example inputs that should match (and 1-2 that shouldn't)
   - Reviewer: jurist (for the citation) + methodologist (for the
     regex quality)

## Updating an existing rule (statute amended)

When an instrument is amended (e.g., POEA MC 14-2017 superseded by
RA 11641 in 2022):

1. **Don't delete the old rule.** Keep it but flag with `last_amended`
   and `superseded_by` fields:
   ```python
   {
       "rule":         "ph_hk_zero_fee_poea_mc_14_2017",
       "pattern":      r"(?i)poea\s*mc\s*14[\-]?2017",
       "citation":     "POEA MC 14-2017 (PH→HK zero placement fee)",
       "severity":     "high",
       "ilo_indicator": ["fee_violation"],
       "category":     "corridor_caps",
       "last_amended": "2022-12",
       "superseded_by": "RA 11641 §3 (Department of Migrant Workers Act)"
   }
   ```

2. **Add a new rule** for the superseding instrument.

3. **The grader's `_AUTHORITATIVE_STATUTES_ALLOWLIST` should include
   both** so a model citing either gets credit.

## How the GREP layer fires at runtime

```
USER PROMPT
    ↓
_grep_call(prompt_text)
    ↓
for rule in GREP_RULES:
    if re.search(rule["pattern"], prompt_text):
        hits.append({
            "rule":         rule["rule"],
            "citation":     rule["citation"],
            "severity":     rule["severity"],
            "match_excerpt": <substring around the match>
        })
    ↓
{"hits": [...], "elapsed_ms": ...}
    ↓
prepended to Gemma's context as:
    "GREP findings:
     - [ILO C029 §2 + Indicator 4] debt_bondage_with_passport_retention:
       'passport. they kept until debt'
     - [...]"
```

## Common pitfalls

1. **Over-broad regex.** A pattern like `(?i)passport` matches every
   prompt that mentions passports — false positive on benign cases.
   Always include 2+ tokens.

2. **Missing case-insensitive flag.** `(?i)` at the start of every
   pattern unless you explicitly need case sensitivity (very rare).

3. **Anchor-less patterns.** A pattern like `(?i)debt` matches "credit
   card debt" which isn't trafficking. Use word boundaries `\b` and
   require ≥2 contextual tokens.

4. **Not tagging the ILO indicator.** Without `ilo_indicator`,
   downstream cross-referencing (with the 11-indicator manual) fails.

5. **Severity inflation.** Tagging everything as "critical" floods
   the response with warnings. Use the scale honestly.

## See also

- [`rag_corpus.md`](rag_corpus.md) — for adding statute documents
  (companion to GREP rules that fire on those statutes)
- [`../contributing_curator_blocks.md`](../contributing_curator_blocks.md)
  — for adding the statute to `_authoritative_statutes.json`
- [`../component_diagram.md`](../component_diagram.md) — how the
  GREP layer fits in the request flow
