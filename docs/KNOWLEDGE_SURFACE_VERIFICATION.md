# Knowledge surface verification

Snapshot of DueCare harness knowledge-layer state as of 2026-07-28.
Re-runnable via `.venv\Scripts\python.exe scripts/verify_knowledge_surfaces.py`
on Windows or the equivalent repository interpreter elsewhere.

> Scope: this snapshot covers the **trafficking knowledge layer** (GREP / RAG / templates /
> personas / ILO conventions, etc.). The separate propose-only **entity-intelligence layer**
> (official-registry verification, the 1,111-source catalogue, 532 support organisations) is
> documented with its own counts in
> [`entity_intelligence_pipeline.md`](entity_intelligence_pipeline.md); it does not change
> the surfaces below.

## Counts

| Surface | Count |
| --- | --- |
| `GREP_RULES` | 451 (categories A through GGGG + HHHH + IIII + MMMM + NNNN, including SCREENING + AAA-III + JJJ-OOO + PPP-YYY + ZZZ-GGGG) |
| `RAG_CORPUS` | 865 (incl. 6 landmark case-law + 3 national anti-trafficking units + research / faith / sex-worker-rights bodies + US HSI / CBP CEE / UK IASC / GRETA / 3 UN SR mandates / MPI / Asia Foundation / Amnesty / BHRRC / Solidaridad cluster / ECPAT / HRW + IMO/ITF + ICAT + AU/Ouagadougou + ASEAN ACTIP detail + Lanzarote + GCM + UFLPA + C189/C188/MLC 2006/Palermo Art 3/P029 sector-convention docs + migrant-worker conventions ILO C097/C143/ICRMW + IRIS + BD/ID/LK/IN origin-state laws + Kuwait DW law + US TVPA + AU/CA supply-chain acts + CoE Warsaw + MLC 2006 recruitment/repatriation/agreement detail + C155/C187 OSH + 2022 OSH-as-fundamental-principle) |
| `MULTIDOMAIN_CORPUS` (`harness/_multidomain_corpus.py`) | 610 (51 integrity verticals across UN SDGs 1-17; opt-in BM25 at `GET /api/multidomain/rag` and `/api/harness-catalog/multidomain`; deliberately kept separate from the trafficking `RAG_CORPUS` so anti-trafficking prompts and retrieval never commingle with off-domain content) |
| `CORRIDOR_FEE_CAPS` | 38 |
| `FEE_CAMOUFLAGE_DICT` | 57 |
| `NGO_INTAKE` | 36 |
| `ILO_CONVENTIONS` | 19 |
| `ILO_INDICATORS` | 11 |
| `TEMPLATES_REGISTRY` | 36 |
| Personas (`_personas.json`) | 37 |

## What is in each surface

### `GREP_RULES` (451 detection patterns)

Multi-category pattern detection across the recruitment + deployment
+ exploitation lifecycle, organised A through OOO + HHHH + IIII + MMMM + NNNN:

| Cluster | Categories | Theme |
| --- | --- | --- |
| Core | A-J | Original DueCare detection set (debt bondage, fee camouflage, document retention, kafala, GBV, contract substitution, isolation, threats, supply-chain audit, jailbreak) |
| Sex / vulnerability | EE-GG | Sex-trafficking, vulnerability targeting, religious-cover recruitment |
| Sectoral | HH-II | Fishing vessel, compound-scam recruitment |
| Visa-cover | JJ | Athlete / cultural-exchange visa abuse |
| Normal-query | KK | Worker FAQ triggers (prevent over-refusal) |
| Recovery | LL | Recovery + restitution + reintegration |
| Pretext | MM | High-risk scam-cover pretexts |
| Gig-platform | NN | Uber / Lyft / Deliveroo / Grab algorithmic exploitation |
| Seasonal-visa | OO | US H-2A / H-2B / AU PALM / CA SAWP |
| Refugee | PP | Refugee / displaced-person leverage |
| AI fraud | QQ | Deepfake / synthetic recruitment fraud |
| Child | RR | Orphanage tourism, sport academy, child marriage |
| Organ | SS | Organ trafficking + transplant tourism |
| Forced marriage | TT | Marriage visa as labour cover |
| Anti-union | UU | Worker organising suppression |
| Conflict | VV | War zone + post-disaster recruitment |
| DV intersection | WW | Domestic violence x labour trafficking |
| Medical | XX | Nurse / caregiver recruitment fraud |
| Tourism | YY | Tourism + cruise crew exploitation |
| High-skill visa | ZZ | H-1B / Blue Card / TSS 482 / Skilled Worker |
| Screening | SCR | Validated-screening-tool disclosure patterns |
| Dating-app / biometrics / pension | AAA-CCC | Dating-app pretext, biometric-coercion, pension denial |
| Refugee leverage / subcontracting | DDD-EEE | Refugee-leverage extended, multi-tier subcontracting |
| Online sex / sports / US sectoral | FFF-HHH | OnlyFans cover, boxing camp, nail salon + massage + hotel housekeeping |
| Criminal exploitation | III | Drug mules, county-line youth, begging rings, foster-care pipeline |
| Chain-migration | JJJ | Send-for-child pattern, child separation for remittance |
| Working-holiday | KKK | US J-1 SWT, AU WHM 417/462 |
| Port / offshore | LLL | Stevedore subcontracting, offshore oil/gas rig |
| Diplomatic household | MMM | A-3/G-5, UK ODWPH |
| Faith-worker | NNN | R-1 + UK Tier 2 Minister of Religion |
| Extractive mining | OOO | Artisanal + small-scale gold/3TG/cobalt/mica |
| Sector conventions + cross-corridor | HHHH | ILO C189 domestic-work confinement/rest, C188 fishing vessel, MLC 2006 seafarer fees/abandonment, contract substitution, passport "safekeeping" euphemism, Palermo act+means |
| Stacked manipulation + false legitimacy | IIII | Combined/layered manipulation patterns + false-legitimacy framing |
| Sham status / misclassification | MMMM | Sham employment-status / employment-misclassification (unpaid "training", "self-employed" with employer control, intern-doing-full-job, au-pair-as-full-domestic, tithe/obedience wage control), citing ILO C095 / R198 |
| Digital recruitment + payment rails + corridor depth | NNNN | App/platform recruitment, crypto + e-wallet fee rails, Gulf "free visa" scam, student-visa labour, document-confiscation euphemisms, kafala mobility, exit/release fees, + Ethiopia/East-Africa/South-Asia corridors; citing ILO C181 Art. 7 + Fair Recruitment 2016 + ICRMW Art. 21 |
| Coercive debt-collection + debt-laundering | OOOO | Predatory-lending / debt-bondage cluster: passport-as-loan-collateral, fake "savings"/deposit schemes, arbitrary balance inflation, guarantor coercion, third-party harassment, public doxxing, fabricated criminal accusations, immigration blacklisting threats, payment-rail structuring, cross-border proceeds layering, shell-company collector rotation, licensed-agency chop pass-through; citing ICRMW Art. 14/21/22 + Supplementary Slavery Convention 1956 Art. 1(a) + ILO C095 + FATF Recs 10/24/32 |

### `RAG_CORPUS` (865 knowledge documents)

ILO conventions, UN instruments, regional anti-trafficking treaties,
destination-country statutes, origin-country statutes, bilateral
MOUs, sectoral standards, supply-chain transparency laws, screening
questionnaires, complaint procedures, tech-platform Trust & Safety
policies, NGO / civil-society frameworks, and 15 public-record
case-study summaries (Rana Plaza, Qatar World Cup, Thailand fishing,
Mauritania, Eritrea, North Korea, Cuba medical missions, UFLPA /
Xinjiang, Operation Blooming Onion, IOM Libya, GEFM Brazil, CIW
Florida, Saipan, Bangladesh tea estates, ID-SA 2011 moratorium).

### `CORRIDOR_FEE_CAPS` (38 entries)

Versioned corridor and programme fee-rule entries across the established
South/Southeast Asia to Gulf/East Asia paths plus selected seasonal-worker
programmes. The count is measured from the current dictionary; it is not a
claim that every possible origin/destination pair has an active rule.

### `FEE_CAMOUFLAGE_DICT` (57 deceptive fee labels)

Labels grouped: training / orientation, medical, process,
deployment / placement, broker / agent, document / clearance,
deposit / bond, salary-deduction, novation / loan-transfer,
sectoral (P3MI / RA / SPE / manpower).

### `NGO_INTAKE` (36 corridors + regions)

Per-corridor NGO + regulator + embassy + POLO contact bundle,
plus cross-region patterns (`('any', us)`, `('any', uk)`,
`('any', eu)`, `('survivor', 'global')`).

### `ILO_CONVENTIONS` (19 conventions)

C029, C087, C095, C097, C098, C100, C105, C111, C138, C143, C181,
C182, C188, C189, C190, P029. Each entry has key articles +
focus + ratification note.

### `TEMPLATES_REGISTRY` (36 complaint + narrative templates)

The registry includes origin- and destination-country regulator complaints,
NGO/IOM/NRM and hotline referrals, worker and survivor narratives, wage and
passport demands, fee-refund and loan-void demands, contract-substitution
complaints, witness and affidavit formats, restitution calculations, supplier
audit findings, and UNGP/OECD remediation requests. The executable verifier
prints every template ID plus its field and required-field counts so category
copy cannot silently become a competing inventory.

### Personas (37 system-prompt roles)

The versioned `_personas.json` registry contains 37 roles spanning worker,
caseworker, NGO, legal, regulator, research, platform-safety, medical,
financial-intelligence, maritime, compliance, policy, engineering, and
community-support viewpoints. The JSON registry and its schema are canonical;
this page deliberately avoids duplicating all role definitions.

## Smoke render test

`scripts/verify_knowledge_surfaces.py` smoke-renders the
`passport_return_demand` template with a synthetic sample dict
and confirms:
- Body literal 4,076 characters
- Rendered output 4,076 characters
- 0 unfilled `{{placeholder}}` tokens
- Pre-filled legal citations appear verbatim (ILO C189 Art. 9,
  Palermo Protocol Art. 3, Vienna Convention on Consular
  Relations Art. 5(d), HK Cap. 57 Sec. 32 + Cap. 57A Reg. 13)

The same pattern works for all 36 templates in the registry: any
template whose required fields are filled produces a complete
court-ready or NGO-ready document with no unresolved
placeholders.

## Gemma 4 verification path

`templates.py` exposes `gemma_fill_template(template, bundle, manual_fields, gemma_call)`,
a three-pass renderer:

1. **Pass 1** -- deterministic source-hint extraction from the
   case bundle (`intelligence.case_brief`,
   `intelligence.ilo_indicators`,
   `intelligence.evidence_edges`, `people[0].label`, etc.).
2. **Pass 2** -- manual caseworker overrides (always
   authoritative).
3. **Pass 3** -- Gemma 4 orchestration for remaining gaps with a
   strict no-fabrication prompt + JSON-only response + valid-
   field-id guardrail.

Per-field provenance is tracked (`manual` / `bundle_hint` /
`gemma` / `missing`) and surfaced to the UI through the
`/api/templates/render` payload.

## Syntax + file integrity

All critical files parse cleanly:

| File | Lines | Status |
| --- | --- | --- |
| `packages/duecare-llm-chat/src/duecare/chat/templates.py` | 5,647 | AST OK |
| `packages/duecare-llm-chat/src/duecare/chat/harness/__init__.py` | 7,410 | AST OK |
| `packages/duecare-llm-chat/src/duecare/chat/harness/_grep_rules.py` | 9,688 | AST OK |
| `packages/duecare-llm-chat/src/duecare/chat/harness/_rag_corpus.py` | 3,471 | AST OK |
| `packages/duecare-llm-chat/src/duecare/chat/harness/_multidomain_corpus.py` | 2,451 | AST OK |
| `packages/duecare-llm-chat/src/duecare/chat/harness/_personas.json` | -- | JSON OK |
| `kaggle/01-duecare-exploration-workbench/kernel.py` | 3,402 | AST OK |
| `kaggle/02-live-demo/kernel.py` | 2,093 | AST OK |
| `kaggle/A-00-omni-experiment-workbench/kernel.py` | 10,544 | AST OK |

## Runtime boundary

The 2026-07-28 receipt ran successfully with the repository `.venv`.
`scripts/verify_knowledge_surfaces.py` intentionally uses AST and JSON standard
library parsing rather than importing the application stack, so this check is
portable and does not prove that optional runtime dependencies or external
services are available. Kaggle kernels retain their own explicit dependency
bootstrap and are validated separately.

The same maintenance cycle reviewed the 12 candidate corridor-source URLs:
seven responded directly, two redirected, three were transient or bot/network
limited, and zero were confirmed broken. Reachability is not rights approval;
all 12 remain blocked from training as recorded in the dated
[closeout receipt](CLOSEOUT_RESOLUTIONS_2026_07_28.md).

## Re-run

```powershell
.\.venv\Scripts\python.exe scripts/verify_knowledge_surfaces.py
```

Exit code 0 = pass; non-zero = AST or JSON error somewhere in
the surface.
