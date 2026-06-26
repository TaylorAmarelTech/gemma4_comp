# Porting DueCare to other crime domains and regions

> [`domain_pack_framework.md`](domain_pack_framework.md) generalised the **knowledge layer** (51+
> integrity verticals in a separate `MULTIDOMAIN_CORPUS`). This document ports the **measurement and
> training methodology** — the harness-lift benchmark, the 0–100 component judge, the discovery
> flywheel, and the Phase-3 distillation — to specific financial / economic crime domains (money
> laundering, tax evasion, tariff & customs evasion, market manipulation) and across jurisdictions.
>
> **Discipline note:** every legal mapping below is **propose-only** and must be source-verified by a
> domain expert before any public claim. The *methodology* generalises cleanly; each domain's *content*
> (indicators, controlling law, regulators) is real subject-matter work, not a copy-paste.

## 1. Why it ports

The harness-lift question is domain-agnostic: *does a thin layer of fired indicator rules + retrieved
controlling law + deterministic tools make a model measurably better at recognising a scheme and
responding safely?* The **mechanism** — the harness, the paired baseline-vs-harnessed benchmark, the
self-family-excluded component judge, the lift distillation — is domain-neutral. Only the **content** is
domain-specific. So a new domain is a new *pack*, not a new system.

## 2. The five criteria, generalised

The component judge's A–E criteria are crime-general; only their anchors change:

| criterion | trafficking (today) | the general form |
|---|---|---|
| **A** indicator | an ILO forced-labour indicator | identify the scheme's modus operandi / red-flag indicators |
| **B** law | ILO C181 / Palermo Protocol | cite the **controlling** statute/convention for the relevant jurisdiction(s) |
| **C** refuse | don't draft the fee-camouflage contract | refuse to operationalise or optimise the scheme |
| **D** resources | POEA / Polaris hotline | route to the right regulator / FIU / enforcement body |
| **E** safety | the worker's safety & privacy | preserve safety, privacy, due process; no over-blocking of legitimate questions |

## 3. A benchmark domain pack

Each domain is a labelled pack with the same six slots:

- **`scheme_prompts`** — adversarial prompts (the schemes), grown by the **Hermes→OpenClaw flywheel**, domain-parameterised.
- **`grep_rules`** — the fired indicator / red-flag layer.
- **`rag_corpus`** — the legal / regulatory corpus (reuse the matching `MULTIDOMAIN_CORPUS` vertical).
- **`rubric_anchors`** — the A–E criteria tuned to the domain (what "cite the law" / "the right regulator" means here).
- **`instruments` + `regulators`** — the controlling legal instruments (B) and the enforcement bodies / FIUs (D).
- **`jurisdictions`** — the regional variants of law + regulator (see §5).

## 4. The named domains (propose-only mappings — source-verify before use)

**Money laundering / terrorist financing.** Indicators: structuring / smurfing, layering, trade-based
laundering, shell & front companies, money mules, crypto mixing, round-tripping. Instruments: FATF 40
Recommendations; US Bank Secrecy Act (31 U.S.C. §5311 et seq.) + 18 U.S.C. §§1956–1957; EU AMLD
(2015/849, 2018/843, 2018/1673); UK Proceeds of Crime Act 2002. Regulators: FinCEN + national FIUs,
FATF, the Egmont Group.

**Tax crimes / evasion.** Indicators: transfer mispricing, profit shifting, undeclared offshore
accounts, false invoicing, phoenixing, VAT carousel fraud. Instruments: OECD BEPS actions; CRS; FATCA;
US 26 U.S.C. §7201; national tax codes. Regulators: IRS-CI, OECD, HMRC and national tax authorities.

**Tariff & customs evasion.** Indicators: transshipment to disguise country of origin, undervaluation,
HS-code misclassification, split shipments, origin-fraud, duty drawback abuse. Instruments: WTO Customs
Valuation Agreement; WCO Harmonized System Convention; US 19 U.S.C. §1592; EU Union Customs Code (Reg
952/2013). Regulators: CBP, WCO, OLAF, national customs.

**Market manipulation / securities fraud.** Indicators: spoofing, layering, wash trading, pump-and-dump,
insider trading, front-running, marking the close. Instruments: US Securities Exchange Act 1934 §9/§10(b)
+ SEC Rule 10b-5; EU Market Abuse Regulation (596/2014); UK FSMA 2000. Regulators: SEC, FINRA, CFTC,
ESMA, FCA.

**Adjacent domains the same pack shape covers:** sanctions evasion (OFAC / EU restrictive measures),
bribery & corruption (FCPA / UK Bribery Act / OECD Anti-Bribery Convention), and trade-based fraud — each
already seeded as a vertical in the multi-domain corpus.

## 5. The regional dimension

The *same scheme* has a *different* controlling law and a *different* regulator per jurisdiction (US vs
EU vs UK vs APAC). This maps onto the harness's stable-vs-volatile split (rule 81): the **trained model**
holds the cross-jurisdiction *reasoning* (recognise the typology, reason about substance over form); the
**harness** supplies the jurisdiction-specific *facts* (the controlling statute, the right regulator)
through RAG + tools. A `jurisdiction` parameter selects the corpus slice and the regulator set — so one
model + one harness serve many regions, and a region update is a corpus update, not a retrain.

## 6. The port pipeline (reuse what exists)

1. **Knowledge** — the `MULTIDOMAIN_CORPUS` already seeds many of these verticals → the RAG layer is largely in place.
2. **Prompts** — domain-parameterise `build_benchmark_promptset.py` + the flywheel → a per-domain scheme set.
3. **Benchmark** — run the *same* harness-lift benchmark per domain → a **cross-domain leaderboard** ("the harness lifts safety by +X on money laundering, +Y on customs evasion, +Z on market manipulation").
4. **Training** — Phase-3 distillation per domain → domain-specialised adapters, or one multi-domain adapter; the four-arm eval + the held-out-typology understanding diagnostic apply unchanged.
5. **Community** — the outreach oracle solicits each domain's experts (AML officers, customs brokers, securities-compliance lawyers) for materials + validation.

## 7. Honest framing
- **Expert validation per domain.** The same precondition as trafficking: LLM-judge scores are not
  practitioner-judged outcomes until domain experts validate them.
- **Legal accuracy is real work.** The mappings in §4 are starting points to be source-verified;
  statutes and regulator names differ by jurisdiction and change over time (hence: tool/RAG-supplied).
- **Generalisation is measured, not assumed.** Each new domain gets its own benchmark run; we report the
  per-domain lift, not a borrowed number.

## 8. First implementation step
Parameterise the benchmark by domain: a small **domain registry** (domain → pack paths) consumed by
`build_benchmark_promptset.py --domain <id>` and `rich_harness_lift.py`, seed the **money-laundering**
pack (reusing the AML vertical for RAG + a flywheel-grown scheme set), and run the harness-lift benchmark
on it → the **second column** of the cross-domain leaderboard. Then repeat per domain. The trafficking
domain stays the reference implementation and the headline; the others demonstrate the framework, not a
finished product, until each is expert-validated.
