# Claim epistemics — rules for rumour, faith-framing, control narratives, and misunderstood "law"

**The question (Taylor, 2026-07-10):** *do we need rules and guidance around false rumours, or information
routed in faith rather than law, misunderstood facts, that deserve additional verification and validation?*

**Yes — and it is load-bearing for the anti-trafficking mission.** Traffickers and abusive recruiters do not
only break the law; they **impersonate** it. Control is manufactured with false "rules" ("your passport
belongs to the employer", "you must work off your debt before you can leave", "you signed, so you can't
quit"), with faith and community pressure ("it's haram to break your contract", "have faith, trust the
agency"), with rumour ("everyone says the embassy will deport you if you complain"), and with honest
**misunderstandings** of real rules ("kafala means you can never change jobs"). A safety harness that repeats
any of these as if it were the law fails the worker. So the harness needs an explicit **epistemic-status**
layer, separate from the law layer, that says *what kind of claim this is* and *what to do about it*.

Implementation: `scripts/claim_epistemics.py` (deterministic, no model, no network, propose-only) +
`tests/test_claim_epistemics.py`. It complements — does not replace — the existing layers:
`legal_claims.py` / `legal_reasoning.py` (the **law**, with exceptions + freshness), `reasoning_contract.py`
(procedure-not-facts + the fragile-fact rule), and `redteam_classify.py` (response behaviour).

## The eight epistemic statuses

| Status | What it is | Posture |
|---|---|---|
| `law` | a statute / regulation / court decision | cite it and apply it **with its exceptions**; verify volatile figures |
| `official_guidance` | ILO / UN / FATF soft-law, indicators | cite as **guidance**, not binding law; pair with the binding rule if one exists |
| `verified_fact` | a documented empirical fact | use it, keep the source, flag if volatile |
| `folk_belief_or_rumor` | a community belief, unsourced ("everyone says", "I heard") | **do not present as law**; verify against a primary source first |
| `faith_or_moral_framing` | advice framed as a religious/moral obligation, presented as binding | respect the belief, but **separate faith from law** and give the actual legal position |
| `control_narrative` | a false "rule" used to coerce/mislead a worker (the abuser's "law") | **actively COUNTER**: state the correct position, name who can help, never repeat the false rule |
| `misunderstanding` | a plausible **over-simplification** of a real rule | correct with the accurate, **scoped** rule (many "you can never…" claims are outdated) |
| `unclear` | no decisive marker | treat as unverified; route to a primary source / a human |

**The rule of the layer:** anything that is **not** `law` / `official_guidance` / `verified_fact` MUST be
surfaced as *"needs verification — this is not established law,"* and a recognised **control narrative** must
be **countered**, not merely flagged. A signature, a religious framing, a rumour, or a beneficiary's
say-so does not convert a coercive claim into the law.

## Beneficiary-aware detection (law-washing)

The same sentence can be a legitimate legal statement or a coercion tactic depending on **who is asserting
it and why**. "Under the labour law you must stay until the contract ends" reads as a (verifiable) legal
claim on its own — but asserted by the **employer/recruiter/agency/sponsor** to keep a worker from leaving,
it is a **control narrative** even though it name-drops "the law." `classify_epistemic_status(text,
attributed_to=...)` encodes this: a rule that traps the worker, asserted by the party who benefits, is
treated as coercion. This is the "information routed in faith rather than law" risk generalised to
"information routed through the abuser's authority rather than a verifiable source."

## Myth → reality catalog

`MYTH_CATALOG` pairs the most common weaponised false rules with the correct legal position **and a real
anchor id in the legal-claim library** (a test asserts every anchor resolves — no dangling citations):

- *"Your passport belongs to your employer"* → it is the worker's; retention is an offence in many
  destinations and a forced-labour indicator (`th_…`, `my_…`, `jo_…`, `ilo_indicators_2025`).
- *"Work off your debt before you can leave"* → debt-tied-to-exit is **debt bondage**, not a lawful rule
  (`c029_definition`, `ilo_indicators_2025`, `c181_recruitment_fees`, `ilo_fair_recruitment`).
- *"It's haram to break your contract"* → a moral framing is not a legal obligation; a contract cannot waive
  forced-labour protection (`c029_definition`, `coe_warsaw_trafficking`).
- *"The embassy will deport you if you complain"* → embassies/attachés assist; the **non-punishment**
  principle protects victims (`coe_warsaw_trafficking`, `ilo_p029_forced_labour_protocol_2014`).
- *"Kafala means you can never change jobs"* → outdated/overbroad; several states have reformed
  (`sa_kafala_reform_2025`, `qa_wage_protection`, `bh_lmra_flexi_permit`).
- *"You signed, so it's binding"* → a signature does not make an unlawful term lawful.
- *"Free visa, free ticket = guaranteed free job"* → a slogan, not a guarantee; often irregular.
- *"Fishers / domestic workers have no rights"* → dedicated instruments exist (`mlc_2006`, `ilo_c188_fishing`,
  `c189_domestic_workers`).

## How it connects to the rest of the harness

- It is the **epistemic** counterpart to the deterministic **law** layer: `legal_reasoning.py` says *what the
  law is*; `claim_epistemics.py` says *whether the claim in front of us is law at all*.
- It reinforces the `reasoning_contract` thesis: the model should carry the **procedure** (name the
  indicator → cite the controlling law → protective action → resources) and treat any volatile or
  authority-sourced "rule" as something to **verify**, not memorise or repeat.
- A natural next step (owed): route a `control_narrative`/`misunderstanding` assessment into the response
  path so the harness surfaces the myth→reality correction inline, and add the origin/host-language markers
  (the classifier is English-only today — the same limitation flagged for the GREP and red-team layers).

## Limitations (stated, not hidden)

- Deterministic marker-matching: it will miss paraphrases and non-English phrasings; it is a **screen**, and
  an `unclear` result routes to verification rather than a guess.
- The catalog is a starter set (8 entries) — high-frequency control narratives; it is meant to grow through
  the same gated, build-upon process as the legal corpus.
- Propose-only: nothing is wired into the live harness response path yet; adoption is gated.

## Reproduce

```
python scripts/claim_epistemics.py        # demo across all statuses + the myth->reality catalog
```
