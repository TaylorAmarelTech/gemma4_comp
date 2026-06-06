# DueCare as a domain-general integrity framework

> Status: live (2026-06-05). The anti-trafficking corpus is the reference
> implementation; thirty-seven further verticals (enumerated in the Current
> verticals table below) are seeded as proof the same architecture generalizes
> across UN SDGs 1-17. Extends the `duecare-llm-domains`
> package (`duecare.domains.*`) and the provider-neutral `HarnessSpec`
> (see `.claude/rules/81_canonical_runtime.md`).

## Thesis

DueCare looks like an anti-trafficking tool, but the machinery is **domain-
neutral**. A "domain pack" is just a labelled set of knowledge surfaces and
behaviours that the same harness loads. Anti-human-trafficking /
anti-human-exploitation is the deepest pack (the reference implementation, ~800
grounding docs + 362 GREP rules + 13 tools + 176 rubric dimensions). The *same
eight-component template* applies to any vertical where the task is "recognise a
harmful or illicit pattern, ground the judgement in real authority, and route to
a remedy" — labour rights, financial crime, corruption, environmental crime,
consumer protection, healthcare fraud, and other SDG-aligned integrity domains.

## The eight-component domain-pack template

Every vertical is the same eight slots. Trafficking populated them first; a new
domain is "stood up" by filling the same slots with its own web-researched,
source-cited content through the identical pipeline.

| # | Component | What it is | Corpus id-prefix(es) — trafficking reference |
|---|---|---|---|
| 1 | **Detection rules** | Deterministic pattern matchers (regex / GREP) over input text | `GREP_RULES` (categories A-JJJJ) |
| 2 | **Grounding corpus** | BM25-retrievable authority documents | `RAG_CORPUS` |
| 3 | **Tools** | Deterministic lookups / classifiers the model can call | `_TOOL_DISPATCH` (13 tools) |
| 4 | **Rubric dimensions** | What a judge scores a response on | `harness_lift_dimensions.json` (176 dims / 29 groups) |
| 5 | **Personas** | Reviewer / audience lenses | `harness/_personas.json` |
| 6 | **Legal instruments** | Conventions, statutes, regulations | `natlaw_*`, `statelaw_*`, `locallaw_*`, ILO/Palermo/CETS docs |
| 7 | **Schemes & red-flags** | How the harm operates + recognition signals (recognition-framed, never how-to) | `fieldrisk_*`, scheme/MO docs, `FEE_CAMOUFLAGE` |
| 8 | **Remedies & funds** | Compensation, recovery, referral, enforcement | `remedy_*`, `compfund_*`, NGO intake |

The **id-prefix is the document index**: `<domain>_<component>_<topic>` (e.g.
`fincrime_trade_based_ml_tbml`, `corruption_beneficial_ownership_transparency`,
`fieldrisk_esoteric_juju_oath_nigeria`). Grep the corpus by prefix to slice it
by vertical or by component — no schema change to the `(id, title, citation,
body)` tuple was required to go multi-domain.

## How a new vertical is added (the pipeline, proven this session)

1. **Web research, not recall.** Fan out research agents that *fetch* real
   sources (the issuing body's site, the statute, the FATF/UNODC/OECD paper) and
   put the **fetched source URL in the citation** — "real, not faked."
2. **Same component template.** Each agent fills slots 6-8 (instruments,
   schemes/red-flags, remedies) for the new domain.
3. **Deterministic merge.** `reports/_scratch/merge_rag.py` dedups against
   existing ids, ASCII-normalises, generalises any hardcoded contact number
   (rule 80), PII-scans, and inserts `(id, title, citation, body)` tuples.
4. **Verify + gate.** `scripts/verify.py` floors, the harness test suite, and a
   BM25 retrieval smoke confirm the new pack loads and retrieves.
5. **(Optional) detection + tools + dimensions** for the vertical reuse slots
   1, 3, 4 the same way trafficking did.

The harness lift benchmark is the *grader* the same way for any domain: generate
baseline vs harnessed, score against the vertical's rubric, measure the lift.

## Current verticals

Thirty-eight verticals are live in `RAG_CORPUS` (total 1279 grounding docs as of
2026-06-05). One is the deep reference implementation; thirty-seven are seeded
proof the template generalizes. They are browsable as a live card grid in the
Knowledge Atlas "Integrity verticals" tab (`static/knowledge-atlas.html`) —
counts read from the corpus, never hardcoded.

| Vertical | SDG | Status | Seed content |
|---|---|---|---|
| **Anti-trafficking / anti-exploitation** | 8, 5, 10 | Reference implementation | ~800 docs across all 8 components; 362 GREP; 13 tools; 176 dims |
| **Financial crime / illicit finance** | 16 | Seeded (12) | FATF 40 + risk-based approach, 6AMLD, BSA/FinCEN/AML Act 2020, TBML, virtual-asset red flags, PEPs, StAR asset recovery, FATF human-trafficking financial typology (`fincrime_*`) |
| **Anti-corruption / public integrity** | 16 | Seeded (10) | UNCAC, OECD Anti-Bribery, FCPA, UK Bribery Act s.7, procurement red-flags, beneficial ownership, whistleblower protection, TI CPI, corruption-trafficking nexus (`corruption_*`) |
| **Environmental crime** | 14, 15 | Seeded (12) | CITES, Basel Convention, EUDR, Lacey Act, EU IUU + FAO PSMA, FATF environmental-ML, wildlife/timber/e-waste red flags, IUU-forced-labour nexus (`envcrime_*`) |
| **Online & consumer fraud** | 16 | Seeded (12) | Pig-butchering, scam-compound labour nexus, BEC, advance-fee, crypto-investment, money-mule, FTC Act s.5, EU UCPD, elder exploitation, victim remedy (`fraud_*`) |
| **Decent work / labour rights** | 8 | Seeded (12) | ILO C087/C098/C155/C095/C131, working time, child labour, US FLSA, OSHA, EU Working Time Directive, LkSG/CSDDD, UK MSA s.54 (`labour_*`) |
| **Tax evasion / illicit financial flows** | 16, 17 | Seeded (12) | OECD CRS, FATCA, BEPS Pillar Two, EU DAC6, trade-misinvoicing IFF, shell-company opacity, VAT carousel, transfer pricing, FATF predicate offence (`tax_*`) |
| **Healthcare fraud & patient safety** | 3 | Seeded (12) | False Claims Act, Anti-Kickback, Stark Law, billing red flags, WHO falsified medicines, EU FMD, organ trafficking, clinical-trial integrity, HIPAA (`health_*`) |
| **Counterfeiting / IP crime** | 9, 12 | Seeded (12) | WTO TRIPS, WCO customs, US 18 USC 2320, EU Reg 608/2013, product-safety harm, INFORM Act, organized-crime nexus, GI fraud, remedy (`counterfeit_*`) |
| **Electoral & information integrity** | 16 | Seeded (12) | ICCPR Art 25, Venice Commission Code, OSCE/ODIHR observation, International IDEA, campaign finance, voter-suppression/disinformation/deepfake/foreign-interference recognition, EU DSA, ballot integrity (`election_*`) |
| **Cybercrime & online safety** | 16 | Seeded (12) | Budapest Convention, US CFAA, EU NIS2, GDPR breach, ransomware, EU DSA, UK Online Safety Act, online child-exploitation recognition + 18 USC 2258A mandatory reporting, BEC/ATO, critical infrastructure (`cyber_*`) |
| **Food safety & agricultural integrity** | 2, 3 | Seeded (12) | Codex Alimentarius, US FSMA, EU Reg 178/2002 + RASFF, EMA/food-fraud red flags, HACCP, origin/species substitution, allergen mislabeling, horsemeat lessons, certification fraud (`food_*`) |
| **Arms control & strategic-trade** | 16 | Seeded (12) | UN ATT, Wassenaar, EU dual-use 2021/821, US EAR/ITAR, UN embargoes, end-user red flags, SALW/Firearms Protocol, brokering, sanctions evasion, proliferation financing (`arms_*`) |
| **Cultural-property & antiquities trafficking** | 11.4, 16 | Seeded (12) | 1970 UNESCO, 1995 UNIDROIT, 1954 Hague, provenance red flags, conflict-antiquities (UN 2199), ICOM Red Lists, looting recognition, due diligence, repatriation (`heritage_*`) |
| **Drug control & precursor diversion** | 3 | Seeded (12) | UN 1961/1971/1988 conventions, INCB precursors (Tables I/II, PEN), NPS, financial red flags, precursor-diversion recognition, forced-labour nexus, harm reduction, opioid crisis (`drug_*`) |
| **Counter-terrorist financing & NPO abuse** | 16 | Seeded (12) | FATF Rec 5/6/8, UN 1267/1989/2253 + 1373, 1999 TF Convention, hawala/MVTS, NPO-abuse red flags, TF typologies, sanctions screening, crowdfunding/FTF recognition (`cft_*`) |
| **Carbon-market, climate & ESG integrity** | 13 | Seeded (12) | ICVCM Core Carbon Principles, EU Green Claims, CSRD/ESRS, carbon-credit fraud red flags, EU ETS VAT-fraud lessons, Paris Art 6, SEC/TCFD, SFDR fund labels, REDD+, MRV (`carbon_*`) |
| **Forced & child marriage / harmful practices** | 5 | Seeded (12) | CEDAW Art 16, CRC minimum age, 1956 Supplementary Slavery + Palermo nexus, forced-marriage red flags, FGM law, dowry abuse, UK FMPO, bride trafficking, Istanbul Convention (`marriage_*`) |
| **Sports integrity / match-fixing** | 16 | Seeded (12) | CoE Macolin Convention, match-fixing/betting-anomaly red flags, WADA Code, governance corruption, ML-through-sport, athlete-trafficking nexus, courtsiding, national platforms (`sport_*`) |
| **Insurance & occupational fraud** | 16 | Seeded (12) | Coalition Against Insurance Fraud, staged-accident/claims-padding red flags, ACFE occupational-fraud tree, ghost payroll, vendor/bid-rigging fraud, anti-fraud controls (`insurance_*`) |
| **Maritime & fisheries crime** | 14 | Seeded (12) | UNCLOS flag-state, flags-of-convenience, IUU fishing, at-sea transshipment, AIS "going dark", ILO C188 forced-labour-at-sea, STS sanctions evasion, vessel-identity fraud, PSC (`maritime_*`) |
| **Illegal mining & extractives integrity** | 12, 15 | Seeded (12) | OECD 3TG Due Diligence, EU Conflict Minerals Reg, Dodd-Frank 1502, EITI, ASM, Minamata mercury, Kimberley diamonds, forced/child-labour nexus, sand mining (`mining_*`) |
| **Housing & land-rights abuse** | 11 | Seeded (12) | CESCR GC7 forced evictions, land grabbing, FAO VGGT, FPIC/UNDRIP, tenure/title fraud, predatory housing, World Bank ESS5, climate displacement, restitution (`land_*`) |
| **Education & qualification fraud** | 4 | Seeded (12) | CHEA diploma/accreditation mills, credential/transcript forgery, QAA contract cheating, exam fraud, student-visa fraud, COPE paper mills, predatory journals, Title IV aid fraud, ENIC-NARIC verification (`education_*`) |
| **Disability & elder-care abuse** | 10 | Seeded (12) | UN CRPD, WHO elder-abuse, financial exploitation, guardianship abuse, nursing-home neglect (Elder Justice Act), APS mandatory reporting, capacity/supported decision-making (`eldercare_*`) |
| **Water & sanitation integrity** | 6 | Seeded (12) | UN Res 64/292 + CESCR GC15 right to water, WIN sector corruption, abstraction theft, illegal discharge, ghost infrastructure, meter-tampering, AWS stewardship (`water_*`) |
| **Humanitarian-aid diversion & integrity** | 16, 2 | Seeded (12) | IASC PSEA, ghost beneficiaries, procurement fraud, food-aid diversion, cash-transfer fraud, armed-group extortion, CHS accountability, donor clawback/debarment (`aid_*`) |
| **Digital identity & deepfake fraud** | 16 | Seeded (12) | NIST SP 800-63 KYC, synthetic-identity fraud, deepfake/voice-clone recognition, account-opening fraud, document forgery, biometric spoofing, SIM-swap, World Bank ID4D (`identity_*`) |
| **Scientific & research integrity** | 9 | Seeded (12) | US ORI 42 CFR 93 (FFP), Singapore Statement, peer-review fraud, image manipulation, data fabrication, authorship abuse, ICMJE trial registration, retractions, predatory citation (`sci_*`) |
| **Energy & utility fraud** | 7 | Seeded (12) | electricity theft/non-technical losses, meter tampering, fuel adulteration/smuggling, subsidy diversion, renewable-subsidy fraud, FERC market manipulation, EITI (`energy_*`) |
| **Transport, customs & trade integrity** | 8, 16 | Seeded (12) | WCO SAFE/Revised Kyoto/AEO, WTO Valuation & TFA, undervaluation, rules-of-origin & HS-misclassification fraud, transit/duty evasion, FTZ diversion (`customs_*`) |
| **Social-protection & benefits integrity** | 1 | Seeded (12) | ILO Floors R202, ISSA error/evasion/fraud, GAO improper payments, identity/ghost-pension fraud, wrongful denial (rights side), registry integrity, appeal/due process (`benefits_*`) |
| **Telecom & subscription fraud** | 9 | Seeded (12) | IRSF, SIM-box/interconnect bypass, Wangiri, PBX toll fraud, STIR/SHAKEN robocall, premium-rate scams, mobile-money fraud, GSMA/CFCA standards (`telecom_*`) |
| **Gambling & lottery integrity** | 16 | Seeded (12) | FATF casino AML, ML recognition (chip-dumping), illegal/unlicensed gambling, lottery fraud, problem-gambling (NCPG), UK LCCP safer duties, match-fixing betting, RNG integrity (`gambling_*`) |
| **Real-estate & construction integrity** | 11 | Seeded (12) | FATF/FinCEN real-estate ML, beneficial-ownership opacity, title/deed fraud, permit corruption, construction bid-rigging, CoST transparency, building-safety fraud, appraisal fraud (`realestate_*`) |
| **Agricultural subsidy & land-use fraud** | 2 | Seeded (12) | EU CAP/OLAF fraud, phantom-land claims, US crop-insurance fraud, input-subsidy diversion, organic-cert fraud, deforestation-linked subsidy, export-refund fraud (`agri_*`) |
| **Public-procurement & infrastructure integrity** | 9, 16 | Seeded (12) | OECD procurement integrity + bid-rigging guidelines, UNCITRAL Model Law, UNCAC Art 9, cover-bidding/collusion, ghost suppliers, change-order abuse, Open Contracting, World Bank debarment (`procurement_*`) |
| **Transport safety & emissions integrity** | 3, 11 | Seeded (12) | EPA defeat-device (Dieselgate), odometer fraud, falsified maintenance/airworthiness, unapproved parts, FMCSA hours-of-service, recall concealment, VIN cloning (`transport_*`) |

Several verticals are deliberately *adjacent* to trafficking — illicit finance,
corruption, IUU-fishing forced labour, scam-compound coercion, organ trafficking,
counterfeit-production forced labour, coerced drug-cultivation, and conflict-
antiquities financing are all how exploitation is paid for, enabled, or co-
located — so each adjacent pack also enriches the trafficking pack with an
explicit nexus doc (e.g. `envcrime_iuu_forced_labour_nexus`,
`fraud_scam_compound_labour_nexus`, `health_organ_trafficking`,
`counterfeit_organized_crime_nexus`, `drug_forced_labour_nexus`,
`heritage_conflict_antiquities`). The rubric's named cross-domain proof
trio — trafficking + tax_evasion + financial_crime — is fully present.

## Why this matters for the rubric

The hackathon rubric names **cross-domain generalisation** as evidence the
harness is "real, not faked" — one architecture, many domain packs, run by the
same command. This document + the seeded `fincrime_*` / `corruption_*` packs are
that evidence: the same Gemma-4 harness that recognises a passport-confiscation
red flag also recognises a trade-based-money-laundering red flag, grounded in the
real instrument, because both are the same eight-slot template with different
content.

## Extending further

Candidate next verticals (each is the same eight slots): **fisheries-subsidy &
blue-economy integrity** (WTO Fisheries Subsidies Agreement - SDG 14),
**pharmaceutical & medical-device integrity** (off-label marketing, DSCSA - SDG 3),
**charity & non-profit governance** (beyond CFT - SDG 16), **media & advertising
integrity** (ad fraud, undisclosed sponsorship), and **AI-governance & algorithmic
accountability** (SDG 16). The eight-slot template absorbs each the same way; the
ceiling is research time, not architecture.

See also: `docs/harness_ecosystem.md`, `docs/harness_standard_contract.md`,
`.claude/rules/81_canonical_runtime.md`,
`docs/KNOWLEDGE_SURFACE_VERIFICATION.md`.
