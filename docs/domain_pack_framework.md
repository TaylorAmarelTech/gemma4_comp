# DueCare as a domain-general integrity framework

> Status: live (2026-06-05). The anti-trafficking corpus is the reference
> implementation; financial-crime and anti-corruption verticals are seeded as
> proof the same architecture generalizes. Extends the `duecare-llm-domains`
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

| Vertical | SDG | Status | Seed content |
|---|---|---|---|
| **Anti-trafficking / anti-exploitation** | 8, 5, 10 | Reference implementation | ~800 docs across all 8 components; 362 GREP; 13 tools; 176 dims |
| **Financial crime / illicit finance** | 16 | Seeded | FATF 40 + risk-based approach, 6AMLD, BSA/FinCEN/AML Act 2020, TBML, virtual-asset red flags, PEPs, StAR asset recovery, FATF human-trafficking financial typology (`fincrime_*`) |
| **Anti-corruption / public integrity** | 16 | Seeded | UNCAC, OECD Anti-Bribery, FCPA, UK Bribery Act s.7, procurement red-flags, beneficial ownership, whistleblower protection, TI CPI, corruption-trafficking nexus (`corruption_*`) |

The two new verticals are deliberately *adjacent* — illicit finance and
corruption are how trafficking is paid for and enabled — so the cross-domain
proof is also a substantive enrichment of the trafficking pack (the
`fincrime_*` FATF human-trafficking-financial-flows typology and the
`corruption_*` corruption-trafficking-nexus docs bridge the domains).

## Why this matters for the rubric

The hackathon rubric names **cross-domain generalisation** as evidence the
harness is "real, not faked" — one architecture, many domain packs, run by the
same command. This document + the seeded `fincrime_*` / `corruption_*` packs are
that evidence: the same Gemma-4 harness that recognises a passport-confiscation
red flag also recognises a trade-based-money-laundering red flag, grounded in the
real instrument, because both are the same eight-slot template with different
content.

## Extending further

Candidate next verticals (each is the same eight slots): **labour rights /
decent work** (wage theft, OSH, freedom of association - SDG 8), **environmental
crime** (illegal logging/fishing/wildlife - SDG 14/15), **consumer & online
fraud** (scams, mis-selling), **healthcare fraud & patient safety** (SDG 3),
**electoral & information integrity** (SDG 16). Each is stood up by the same
research -> merge -> verify pipeline; none requires a code change to the harness -
only new domain-prefixed knowledge.

See also: `docs/harness_ecosystem.md`, `docs/harness_standard_contract.md`,
`.claude/rules/81_canonical_runtime.md`,
`docs/KNOWLEDGE_SURFACE_VERIFICATION.md`.
