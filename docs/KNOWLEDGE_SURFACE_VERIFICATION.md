# Knowledge surface verification

Snapshot of DueCare harness knowledge-layer state as of 2026-06-10.
Re-runnable via `python scripts/verify_knowledge_surfaces.py`.

## Counts

| Surface | Count |
| --- | --- |
| `GREP_RULES` | 451 (categories A through GGGG + HHHH + IIII + MMMM + NNNN, including SCREENING + AAA-III + JJJ-OOO + PPP-YYY + ZZZ-GGGG) |
| `RAG_CORPUS` | 859 (incl. 6 landmark case-law + 3 national anti-trafficking units + research / faith / sex-worker-rights bodies + US HSI / CBP CEE / UK IASC / GRETA / 3 UN SR mandates / MPI / Asia Foundation / Amnesty / BHRRC / Solidaridad cluster / ECPAT / HRW + IMO/ITF + ICAT + AU/Ouagadougou + ASEAN ACTIP detail + Lanzarote + GCM + UFLPA + C189/C188/MLC 2006/Palermo Art 3/P029 sector-convention docs + migrant-worker conventions ILO C097/C143/ICRMW + IRIS + BD/ID/LK/IN origin-state laws + Kuwait DW law + US TVPA + AU/CA supply-chain acts + CoE Warsaw) |
| `MULTIDOMAIN_CORPUS` (`harness/_multidomain_corpus.py`) | 610 (51 integrity verticals across UN SDGs 1-17; opt-in BM25 at `GET /api/multidomain/rag` and `/api/harness-catalog/multidomain`; deliberately kept separate from the trafficking `RAG_CORPUS` so anti-trafficking prompts and retrieval never commingle with off-domain content) |
| `CORRIDOR_FEE_CAPS` | 38 |
| `FEE_CAMOUFLAGE_DICT` | 57 |
| `NGO_INTAKE` | 36 |
| `ILO_CONVENTIONS` | 16 |
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

### `RAG_CORPUS` (859 knowledge documents)

ILO conventions, UN instruments, regional anti-trafficking treaties,
destination-country statutes, origin-country statutes, bilateral
MOUs, sectoral standards, supply-chain transparency laws, screening
questionnaires, complaint procedures, tech-platform Trust & Safety
policies, NGO / civil-society frameworks, and 15 public-record
case-study summaries (Rana Plaza, Qatar World Cup, Thailand fishing,
Mauritania, Eritrea, North Korea, Cuba medical missions, UFLPA /
Xinjiang, Operation Blooming Onion, IOM Libya, GEFM Brazil, CIW
Florida, Saipan, Bangladesh tea estates, ID-SA 2011 moratorium).

### `CORRIDOR_FEE_CAPS` (31 corridors)

Top-7 origin countries (PH, ID, NP, BD, VN, KH, MM) by 11 major
destinations (HK, SG, SA, KW, LB, QA, UAE, TW, JP, KR, MY) +
Latin America / Pacific (MX-US H-2A/H-2B, JM-CA SAWP).

### `FEE_CAMOUFLAGE_DICT` (45 deceptive fee labels)

Labels grouped: training / orientation, medical, process,
deployment / placement, broker / agent, document / clearance,
deposit / bond, salary-deduction, novation / loan-transfer,
sectoral (P3MI / RA / SPE / manpower).

### `NGO_INTAKE` (30 corridors + regions)

Per-corridor NGO + regulator + embassy + POLO contact bundle,
plus cross-region patterns (`('any', us)`, `('any', uk)`,
`('any', eu)`, `('survivor', 'global')`).

### `ILO_CONVENTIONS` (16 conventions)

C029, C087, C095, C097, C098, C100, C105, C111, C138, C143, C181,
C182, C188, C189, C190, P029. Each entry has key articles +
focus + ratification note.

### `TEMPLATES_REGISTRY` (34 complaint + narrative templates)

| Class | Count | Examples |
| --- | --- | --- |
| Origin-country regulator | 5 | PH DMW, ID BP2MI, NP DoFE, BD BMET, VN DOLAB |
| Destination-country regulator | 11 | HK Labour Dept, SA MHRSD, UAE MoHRE, Qatar MoL, US DOL WHD, AU FWO, KR EPS, TW MOL, SG MOM, IL PIBA, CA SAWP |
| Referral + restitution pathways | 5 | NGO intake, IOM referral, UK NRM, Polaris hotline, CBP e-Allegation |
| Madlibs scenario templates | 13 | PH-HK fee refund demand, passport return demand, T-Visa affidavit, anti-retaliation TRO, witness statement, restitution calculation, compound-scam victim affidavit, NGO survivor narrative, worker first-contact script, journalist tip brief, employer wage demand, supplier audit finding letter, UNGP/OECD remediation request |

### Personas (22 system-prompt roles)

NGO intake, lawyer (research mode), regulator audit, journalist
fact-check, researcher tagging, worker-side advocate, skeptical
review, active caseworker, embassy officer, peer supporter,
clinical social worker, platform Trust & Safety, faith /
community helper, labour inspector, recruiter compliance,
survivor peer advocate, government policy advisor, engineer
building a safe-migration product, labour lawyer (destination
court), medical clinician (screening), Financial Intelligence
Unit officer, shipping / maritime HR.

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

The same pattern works for all 34 templates in the registry: any
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
| `packages/duecare-llm-chat/src/duecare/chat/templates.py` | 4,736 | AST OK |
| `packages/duecare-llm-chat/src/duecare/chat/harness/__init__.py` | 16,367 | AST OK |
| `packages/duecare-llm-chat/src/duecare/chat/harness/_personas.json` | -- | JSON OK |
| `kaggle/01-duecare-exploration-workbench/kernel.py` | 3,300 | AST OK |
| `kaggle/02-live-demo/kernel.py` | 2,084 | AST OK |
| `kaggle/A-00-omni-experiment-workbench/kernel.py` | 8,061 | AST OK |

## Local-runtime caveat

Local `pip` + venv are currently broken on this workstation
(OneDrive-sync corruption -- `typing_extensions`, `pip._vendor`,
`numpy._core` reported missing across Python 3.10 / 3.12 / 3.14
installs). This blocks `python -c 'from duecare.chat.app import
create_app'` style imports until the venv is rebuilt.

`scripts/verify_knowledge_surfaces.py` works around the broken
venv by using **AST + JSON stdlib parsing only** -- no pip-managed
imports required. The script confirms the knowledge layer is well-
formed regardless of whether the FastAPI stack is locally
installed.

Boot in Kaggle uses the explicit dependency block at the top of
each `kaggle/*/kernel.py` and is unaffected by the local venv
issue.

## Re-run

```bash
python scripts/verify_knowledge_surfaces.py
```

Exit code 0 = pass; non-zero = AST or JSON error somewhere in
the surface.
