# Responsible use policy

DueCare is safety research about migrant-worker exploitation. That subject
matter means the project necessarily handles material — adversarial prompts,
recruitment-scheme patterns, records of models behaving badly — that would be
harmful if used for the thing it exists to detect. This document states the
boundaries plainly, so nobody has to infer them.

It follows the structure Google's
[Responsible Generative AI Toolkit](https://ai.google.dev/responsible/docs/design)
recommends: a system-level policy saying what is and is not permitted, sitting
alongside the data cards, limitation statements, and evaluation reporting held
elsewhere in this repository.

## What DueCare is

A **prompt-level safety harness** and an evaluation benchmark for it. The
harness supplies indicator rules, retrieved legal grounding, and deterministic
tools around a language model, and the benchmark measures whether responses
improve on a defined rubric when it is switched on.

## What DueCare is not

Stated as plainly as possible, because these are the misreadings that would do
real harm:

- **Not a detector.** It does not identify traffickers, victims, or criminal
  conduct. Measured improvements are in *response quality on recorded benchmark
  prompts*, not in real-world detection, sensitivity, specificity, or
  prevalence estimation.
- **Not legal advice.** Statutory citations are retrieval targets for grounding
  checks. Laws, fee caps, and contact routes change, and a citation being
  present is not a determination that it applies to any real situation.
- **Not a substitute for a caseworker, lawyer, inspector, or hotline.** Every
  worker-facing surface points to human help rather than positioning itself as
  the answer.
- **Not evidence.** The synthetic evidence images fail forensic checks by
  design and must never be used in legal, journalistic, or investigative
  proceedings.
- **Not a claim about any vendor's model.** Other organisations' models are run
  as measurement subjects on one narrow rubric. That is not a general quality
  ranking.

## Uses that are not permitted

Beyond the [Gemma Prohibited Use Policy](https://ai.google.dev/gemma/prohibited_use_policy),
which applies to Gemma 4 and every derivative here, do not use this project or
anything derived from it to:

- Plan, structure, disguise, or obtain advice on labour exploitation, debt
  bondage, recruitment-fee schemes, document retention, wage withholding, or
  trafficking — including by mining the benchmark corpora for phrasing that a
  model failed to refuse.
- Locate, profile, surveil, or target workers, survivors, or the organisations
  that support them. The organisational directory exists so help can be found,
  not so people can be found.
- Present model output as a legal determination, an official finding, or a
  substitute for professional judgement.
- Represent DueCare, or results produced with it, as reviewed, approved, or
  endorsed by Google. It is not.
- Generate synthetic identity documents for any purpose other than clearly
  labelled testing. Using them to bypass KYC, customs, or border controls is a
  crime in most jurisdictions.

## How the adversarial material is released

The benchmark corpora contain thousands of prompts written in the voice of
someone attempting exploitation. Publishing them is deliberate and follows
established practice for safety benchmarks — without public prompts, nobody can
reproduce or contest a safety claim.

The release is **tiered**, which is the emerging norm for adversarial datasets:

- **Published:** the prompts, their categories, difficulty labels, the grading
  rubric, and the resulting scores. This is everything needed to reproduce,
  audit, or disagree with a result.
- **Withheld:** the verbatim text of model responses that *complied* with a
  harmful request. Those bodies were removed from the public corpus and the
  grade, outcome, and model id retained in their place — see
  `scripts/redact_seed_prompt_responses.py`, whose `--check` mode runs in CI so
  the withholding cannot silently regress.

The reasoning is that prompts plus grades make a claim verifiable, whereas
successful harmful completions mostly transfer operational detail. A benchmark
should let people check the science without functioning as a library of working
attacks.

For the same reason, this repository names, links, and bundles **no
safety-stripped model weights**. Where the harness supports evaluating such a
model — because a safety claim that depends on the base model's refusals should
be tested against their absence — the checkpoint is supplied by the operator
through an environment variable and is empty by default.

## Privacy boundaries

- No real worker data, case files, chat logs, or personal contact details are
  committed to this repository or shipped in any artifact.
- Every person, company, agency, licence number, and case ID in the corpora is
  a fabricated composite. Names are plausible so the benchmark tests realistic
  inputs; none refers to a real organisation.
- The only contact information published is **organisational** — public
  helplines and agency addresses — with per-entry provenance.
- Worker-facing deployments are designed so raw cases stay on the worker's
  device unless that person deliberately creates a sanitised submission.

## Reporting a problem

- **A listed organisation wanting an entry corrected or removed:** open an
  issue on the repository. This will be actioned.
- **A security or privacy concern:** see [`../SECURITY.md`](../SECURITY.md).
- **A factual error in a statutory citation or a benchmark label:** open an
  issue. Corrections to grounding data are treated as defects, not opinions.

## Related documents

| Document | Covers |
|---|---|
| [`COMPETITION_COMPLIANCE.md`](COMPETITION_COMPLIANCE.md) | Rule-by-rule competition compliance |
| [`../NOTICE`](../NOTICE) | Gemma 4 Apache 2.0 attribution and derivative statement |
| [`../LICENSES.md`](../LICENSES.md) | Asset, model, and dependency licensing |
| [`CREDITS.md`](CREDITS.md) | Attribution for people, models, data, and tooling |
| [`reproducibility.md`](reproducibility.md) | Which command regenerates each headline number |
| `configs/duecare/benchmarks/README.md` | What the adversarial corpora contain and why |
