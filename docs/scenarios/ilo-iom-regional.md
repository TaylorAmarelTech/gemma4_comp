# ILO / IOM regional staff — supra-national pattern analysis

> **Persona.** You're a program officer or technical specialist at
> an ILO regional office (Bangkok, Beirut, Buenos Aires, Pretoria,
> Kathmandu), an IOM mission, the OHCHR migrants' rights office,
> a UNHCR protection unit, or a regional NGO consortium (Bali
> Process, GCM follow-up, Regional Support Office for the Bali
> Process, etc.). You don't enforce — you measure, advise, and
> coordinate across countries.
>
> **What this gives you.** A way to standardize pattern analysis
> across multiple countries' complaint data, ground every finding
> in the same ILO-indicator taxonomy, and produce reports that
> finance ministries + member-state regulators can both read.

## TL;DR

| You'd normally... | With Duecare you... |
|---|---|
| Compile country-by-country reports manually with inconsistent indicator coding | Bulk-classify across countries with the same 11 ILO C029 indicator framework |
| Argue with member states about what "trafficking" means in their context | Use the bundled indicator definitions + statute crosswalks; everyone references the same source |
| Draft cross-corridor comparisons in Excel | Run the harness across all corridors; export structured JSON; pivot in your existing BI tool |
| Wait 6-12 weeks for member-state inputs to a thematic report | Self-serve the analysis on publicly-scraped or partner-provided data |
| Refer member states to "best practice" without operational artifacts | Share the bundled domain pack as a reference implementation; member states can fork it |

## Why a supra-national org would care

Three properties:

1. **Common taxonomy.** Every ILO-indicator output is the same 1-11
   classification. A Pakistan-Saudi case + a Mexico-US case + a
   Ukraine-Poland case all roll up to the same indicator framework.
2. **Open source.** No vendor lock-in. Member states can adopt + adapt
   without a procurement contract with you. Operationally portable.
3. **Statute-grounded.** Findings cite the actual statute
   (national + international). Useful for policy briefs that need
   to survive member-state pushback.

## Workflow 1 — Cross-corridor + cross-country comparison

You're producing the regional thematic report on domestic-worker
exploitation. You want to compare patterns across PH-HK, ID-HK,
ID-SG, ID-TW, ET-LB, KE-SA, GH-LB, NG-LB.

```python
import json
from pathlib import Path
from duecare.chat.harness import apply_grep_rules
from duecare.domains.trafficking.lookup import lookup_corridor

corridors = ["PH-HK", "ID-HK", "ID-SG", "ID-TW",
             "ET-LB", "KE-SA", "GH-LB", "NG-LB"]
results = {}

for corridor in corridors:
    cases_path = Path(f"member_state_cases/{corridor}.jsonl")
    if not cases_path.exists():
        continue
    with cases_path.open() as f:
        cases = [json.loads(line) for line in f]

    # Per-corridor aggregate
    indicator_counts = {i: 0 for i in range(1, 12)}
    rule_counts = {}
    for case in cases:
        hits = apply_grep_rules(case["narrative"])
        for h in hits:
            # The bundled rule->indicator mapping
            indicator_counts[h["indicator_number"]] += 1
            rule_counts[h["rule"]] = rule_counts.get(h["rule"], 0) + 1
    results[corridor] = {
        "total_cases": len(cases),
        "indicator_counts": indicator_counts,
        "top_5_rules": sorted(
            rule_counts.items(), key=lambda x: -x[1]
        )[:5],
    }

# Export for your BI / Excel
with open("regional_thematic.json", "w") as f:
    json.dump(results, f, indent=2)
```

Now you have a single JSON that maps every corridor to the same
ILO-indicator framework. Your report's "regional comparison" table
generates from this directly.

## Workflow 2 — Member-state capacity-building

Member states often ask: *"Can you help us build a pattern-detection
tool for our complaints office?"*

Historically: 6-12 month engagement with consultants, custom
software, no portability. Now: *"Here's a pre-built open-source
pack you can deploy on a Mac mini. Here's the extension format
to add your country's specific regulations. Here's the persona
walkthrough for the regulator workflow."*

Refer them to:
- [`docs/scenarios/regulator-pattern-analysis.md`](./regulator-pattern-analysis.md)
- [`docs/extension_pack_format.md`](../extension_pack_format.md) for
  adding their country's regulations
- [`docs/considerations/COMPLIANCE.md`](../considerations/COMPLIANCE.md)
  for their data-handling team's review

## Workflow 3 — Reference implementation for indicator measurement

ILO's own indicator-measurement work has historically used
hand-coded survey instruments (e.g., the 2017 Methodology for the
Measurement of Forced Labour Surveys). Duecare's bundled indicator
mapping + GREP rules can serve as a reference implementation that
member-state national statistical offices fork:

- Use the bundled rule pack as a baseline GREP catalog
- Extend with country-specific patterns via extension packs
- Calibrate against existing survey-based measurements
- Publish the country-extended pack so other countries can adopt

This is the kind of operational artifact ILO Geneva can endorse
as a "reference implementation" without endorsing any specific
deployment.

## What's pre-loaded that helps a regional org

The bundled corpus covers 20 corridors as of v0.9. ILO regional
offices typically work in regional clusters:

| Region | Corridors covered |
|---|---|
| ILO Bangkok (ROAP) | ID-HK, ID-SG, ID-TW, MM-TH, KH-MY, PH-HK, PH-SA, PH-IT, NP-SA, BD-SA |
| ILO Beirut (Arab States) | ET-LB, GH-LB, NG-LB, KE-SA |
| ILO Pretoria (Africa) | GH-LB, NG-LB, KE-SA, ZW-ZA |
| ILO Lima (LATAM) | MX-US, VE-CO |
| IOM Vienna (Europe) | UA-PL, SY-DE |
| OHCHR Geneva | All 20 |

Each corridor includes the origin + destination regulator (your
member-state counterparts) + 2-3 NGO contacts (your civil-society
partners). This is the same directory your team is already
maintaining in spreadsheets — Duecare ships it as code.

## Limitations specific to supra-national work

- **The harness's classification has a US/Anglo bias** despite being
  multi-corridor. The 11 ILO C029 indicators are global; the
  specific phrasing the GREP rules match is English. Languages
  outside the English-test set will under-detect until extension
  packs add native-language patterns. Your regional office can
  contribute these.
- **The harness doesn't replace national statistical offices.**
  GREP-based pattern detection on complaint text is a complement
  to survey-based prevalence estimation, not a substitute. ILO's
  own indicator-measurement methodology is the gold standard.
- **The corpus reflects the maintainer's research, not ILO endorsement.**
  Until ILO formally adopts it, treat the bundled corpus as one
  reference implementation among many.
- **Cross-country data sharing requires legal basis.** Even if your
  regional office can analyze cases from N countries, the underlying
  data may be subject to data-protection rules in each country.
  The harness's hash-only audit log helps; per-country DPIA is
  still your team's responsibility.

## What this enables that wasn't possible before

- **Real-time regional thematic reports.** Member-state inputs no
  longer require manual indicator coding; classification runs in
  seconds against the same framework.
- **Defensible cross-state comparison.** When a member state
  contests a regional finding, you can point to the same rule pack +
  same audit-log schema as the source.
- **Member-state capacity-building at near-zero cost.** Hand them
  the open-source pack + the persona walkthrough; they're up and
  running in 90 minutes.
- **Operational endorsement of indicators that previously lived only
  in PDF reports.** ILO C029 indicators 1-11 are now executable
  code that any member state can run.

## What you can NOT use Duecare for

- ❌ Replace ILO's own forced-labour prevalence estimates. The
  ILO Global Estimates are based on a specific survey methodology;
  the harness is complementary, not equivalent.
- ❌ Issue official ILO findings using the bundled corpus alone.
  The corpus is a reference; official findings require ILO's own
  review + technical sign-off.
- ❌ Bypass member-state national statistical offices. Coordinate
  through them as you normally would.
- ❌ Share case data across states without legal basis. Per-country
  DPIA + data-sharing agreements still apply.

## Day-1 setup (for an ILO regional office)

1. **Get IT security sign-off.** Hand them the threat model + the
   compliance crosswalk + the vendor questionnaire.
2. **Deploy on a regional-office k8s cluster.** Use the Helm
   chart at `infra/helm/duecare/`. Multi-tenant per technical unit
   (ILO Forced Labour Branch, IOM Counter-Trafficking, OHCHR
   Migration, etc.).
3. **Wire to your existing case-management / data warehouse.**
   The OpenAPI 3 schema lets your existing analytics pipeline pull
   structured classifications directly.
4. **Add region-specific extension packs.** Your regional office's
   knowledge of national regulations is the corpus. Codify it via
   the extension pack format.
5. **Train regional partners.** Run a 1-day workshop per
   [`docs/educator_resources.md`](../educator_resources.md) for the
   member-state consular sections + civil-society partners in your
   region.

After 30 days of regional pilot:
- Publish a "lessons learned" memo internally
- Decide whether to recommend wider ILO endorsement
- Identify the 5-10 most-impactful extension-pack additions for
  the bundled corpus + contribute back to the open-source repo

## Adjacent reads

- [`docs/scenarios/regulator-pattern-analysis.md`](./regulator-pattern-analysis.md) — your member-state regulator counterparts
- [`docs/scenarios/embassy-consular.md`](./embassy-consular.md) — the consular-section workflow upstream
- [`docs/scenarios/ngo-office-deployment.md`](./ngo-office-deployment.md) — your civil-society partners' workflow
- [`docs/extension_pack_format.md`](../extension_pack_format.md) — adding your region's specifics
- [`docs/considerations/multi_tenancy.md`](../considerations/multi_tenancy.md) — per-unit isolation
