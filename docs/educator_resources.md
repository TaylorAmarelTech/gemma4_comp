# Educator resources — using Duecare in the classroom

> **Audience.** Social work professors, migration studies faculty,
> AI ethics instructors, journalism schools, law school clinics,
> trainers running NGO capacity-building workshops.
>
> **What this gives you.** Drop-in lesson plans + workshop guides
> + discussion prompts that use Duecare as a concrete teaching
> case. All MIT-licensed for academic + non-commercial use; please
> attribute.

## Why Duecare works as a teaching artifact

It's the rare AI project that's:

- **Concrete enough to demo in class** — students can run the live
  Kaggle notebook on their laptops in 2 minutes
- **Domain-grounded** — every claim cites the actual statute, so
  you can teach the law and the AI in the same lesson
- **Open enough to dissect** — students can read the source, the
  rubric, the threat model, the ADRs, and write critical analyses
  of design decisions
- **Genuinely contestable** — the harness is helpful, not perfect;
  students can find places where it's wrong and design fixes

## Lesson plan archetypes

### 1-hour intro lesson — "How do AI safety harnesses work?"

**Audience.** Undergraduate AI / CS / ethics, no domain expertise
required.

**Pre-class:** students open
[duecare-chat-playground-with-grep-rag-tools](https://www.kaggle.com/code/taylorsamarel/duecare-chat-playground-with-grep-rag-tools)
and submit one question + the response.

**In class:**
- 10 min: the problem (LLM gives wrong / incomplete legal info on
  trafficking-shaped prompts; hand-graded examples)
- 15 min: the four harness layers (Persona, GREP, RAG, Tools).
  Demo the Pipeline modal — show which layer fires for which prompt.
- 15 min: the same prompt with each layer toggled off; observe
  the output drop in quality
- 15 min: discuss — what's the trade-off? When is the harness
  itself the wrong tool? When does it perform worse than the
  unharnessed model?
- 5 min: assignment — pick a prompt the harness gets wrong; design
  a 5th layer that would fix it

**Materials.** The notebook + [`docs/harness_lift_report.md`](./harness_lift_report.md)
(headline numbers).

### 90-minute lesson — "Privacy-by-design in real ML systems"

**Audience.** AI ethics seminar, privacy law class, security
elective.

**Pre-class:** students read
[`docs/considerations/THREAT_MODEL.md`](./considerations/THREAT_MODEL.md).

**In class:**
- 15 min: the threat model — STRIDE across 4 trust boundaries.
  What's the worst-case attacker?
- 20 min: the design choices that follow from privacy-as-non-
  negotiable: on-device default ([ADR-003](./adr/003-on-device-default-cloud-opt-in.md)),
  edge-proxy auth ([ADR-005](./adr/005-tenant-id-from-edge-proxy.md)),
  hash-only audit log, panic-wipe primitive
- 25 min: small-group exercise — pick one of: "what if the
  worker's recruiter compels them to unlock the phone", "what if
  a hostile employer subpoenas the journal", "what if a research
  team wants aggregate data". For each, walk through what
  information leaks vs stays protected
- 25 min: discussion — privacy-by-design vs privacy-by-policy.
  Which design choices in Duecare can't be undone after the fact?
- 5 min: assignment — find one place where the design fails its
  own threat model; propose a fix

**Materials.** Threat model + ADRs + [`docs/considerations/COMPLIANCE.md`](./considerations/COMPLIANCE.md)
(SOC 2 / GDPR / HIPAA crosswalk).

### 3-hour workshop — "Build your own domain extension"

**Audience.** NGO capacity-building, applied AI bootcamp, advanced
undergrad CS practicum.

**Pre-class:** participants install Docker + clone the repo + run
`make demo`.

**In session:**
- 30 min: tour of the bundled domain content — 11 ILO indicators,
  6 corridors, 42 GREP rules, 26 RAG docs
- 60 min: each participant picks a corridor or pattern not in the
  bundled corpus (e.g., GH-LB if they work in Ghana migration; a
  state-specific anti-fraud regulation; a domain-specific scam
  pattern)
- 60 min: build it as an extension pack per
  [`docs/extension_pack_format.md`](./extension_pack_format.md) —
  YAML + Python rule + test prompts
- 30 min: load each participant's pack, demo it firing on the test
  prompts, debug

**Materials.** Extension pack format spec + the bundled domain
content as templates.

### 2-week project — "Reproduce + critique a published harness-lift number"

**Audience.** Graduate ML / NLP class.

**Pre-project:** students read [`docs/harness_lift_report.md`](./harness_lift_report.md)
+ [`docs/scenarios/researcher-analysis.md`](./scenarios/researcher-analysis.md).

**Project structure:**
- Week 1: each student reproduces the +56.5 pp number on a 50-prompt
  subset; documents any discrepancies
- Week 2: each student designs an alternative rubric (a 12-criterion
  rubric on a different domain or sub-domain) and runs the harness
  on / off across 50+ prompts; reports the lift
- Deliverable: a 4-page paper following the format of
  `docs/harness_lift_report.md` with their custom rubric + the
  harness lift on it

**Grading rubric for students:**
- Reproducibility: does the paper pin git_sha + dataset_version +
  model_revision? (10 pts)
- Methodology: is the rubric pre-registered? Is hand-grading
  blinded? (20 pts)
- Sample size: ≥ 50 prompts; report confidence intervals (15 pts)
- Honest reporting: are negative results included? Is harness OFF
  reported separately from harness ON? (20 pts)
- Critique: what's the harness fundamentally bad at on this
  domain? (20 pts)
- Citation discipline: are external citations to law / ILO docs
  verified? (15 pts)

### 1-day NGO capacity-building workshop — "Use Duecare in your casework"

**Audience.** Working caseworkers + lawyers + IT leads at NGOs
serving migrant communities.

**Pre-workshop:** organizer deploys Duecare on a laptop or office
Mac mini per [`docs/scenarios/ngo-office-deployment.md`](./scenarios/ngo-office-deployment.md).

**Schedule:**
- 09:00-09:30 — Welcome + privacy ground rules (no real PII typed
  during workshop)
- 09:30-10:30 — Demo: complete intake walkthrough per
  [`docs/scenarios/caseworker_workflow.md`](./scenarios/caseworker_workflow.md)
- 10:30-11:00 — Break
- 11:00-12:30 — Hands-on: each participant runs the wizard on a
  composite case from their actual practice (names changed)
- 12:30-13:30 — Lunch
- 13:30-14:30 — Reports tab walkthrough; generating intake
  documents; sharing with partner NGOs / regulators
- 14:30-15:00 — Break
- 15:00-16:00 — Q&A: when does it fail? Where does it surprise?
  Which features should ship first in the next release?
- 16:00-16:30 — Each participant fills the [first-deployer feedback
  form](./first_deployer_feedback.md)
- 16:30-17:00 — Wrap: who's adopting? IT support handoff; next
  check-in

**Outputs:**
- N filled feedback forms
- A "this isn't covered yet, please add" list (potential extension
  packs)
- A "what we'd like to share with peer NGOs" list (case studies the
  organizer can publish)

## Discussion prompts (drop-in)

For a class that needs to fill 30 minutes with a substantive
debate, pick one:

### On privacy
- "The Android app's panic-wipe primitive lets a worker erase
  evidence of their own situation. Does this protect them, or does
  it deprive them of evidence they may need later? Who decides?"

### On automation + judgment
- "The harness drafts a refund-claim cover letter with the
  controlling statute. What's the line between 'tool that
  accelerates a lawyer's work' and 'unauthorized practice of law'?"

### On open source + accountability
- "If the harness gives wrong legal advice and a worker acts on it
  to their detriment, who's responsible? The MIT license disclaims
  warranty. Is that morally adequate? Legally?"

### On scope
- "The bundled corpus covers 12 migration corridors out of
  ~200 globally. Workers in uncovered corridors get a 'consult
  local counsel' fallback. Is this an honest limitation, or is it
  the project privileging some workers over others?"

### On comparison
- "Compared to commercial alternatives (Hive, Sift, Microsoft
  Community Sift), Duecare is cheaper, more transparent, and less
  reliable. When does cost matter more than reliability? When does
  transparency matter more than vendor accountability?"

### On the threat model
- "The threat model assumes the worker's adversary may be the
  recruiter, the employer, or the destination-country authorities.
  What if the adversary is the worker's family (e.g., a young
  woman whose family pressured her into the migration)?"

### On the corpus
- "The RAG corpus is 26 hand-curated documents. Should it grow
  to 260? 2,600? 26,000? What's lost when you scale up?"

## Suggested external readings to pair with Duecare

- ILO Global Estimates of Modern Slavery (latest annual report)
- Polaris Project's annual recruitment fraud taxonomy
- Human Rights Watch reports on the kafala system
- Domestic Workers Bill of Rights legislation in your country
- Verité's responsible recruitment toolkit
- Tella by Horizontal (open-source human-rights documentation app)
- Llama Guard 3 paper (for the technical-comparison angle)
- "Disconnecting from the Cloud" — Privacy by Design literature
  for the privacy-by-design angle

## Writing about a Duecare assignment

If a student paper / dissertation references Duecare:

```bibtex
@software{amarel_duecare_2026,
  author       = {Taylor Amarel},
  title        = {Duecare: a content-safety harness for Gemma 4
                  on migrant-worker trafficking risk},
  year         = 2026,
  publisher    = {GitHub},
  version      = {0.1.0},
  url          = {https://github.com/TaylorAmarelTech/gemma4_comp}
}
```

For the headline harness-lift number specifically, also cite
`docs/harness_lift_report.md` with the SHA you ran against.

## Contact for academic use

`amarel.taylor.s [at] gmail.com`, subject `[duecare academic]`.
Specifically helpful for:

- Custom domain extensions for your jurisdiction (we'll point you
  at the extension pack format + likely review your PR)
- Reference letters for grad students who want to cite Duecare in
  their thesis
- Classroom guest sessions (60-90 min Q&A, schedule permitting)

## Reuse of these materials

These lesson plans are MIT-licensed alongside the project. Adapt
freely for your course. Attribution is appreciated but not required
for non-commercial academic use.

If you adapt for commercial use (paid bootcamp, certified course,
etc.), please attribute and link back to
https://github.com/TaylorAmarelTech/gemma4_comp.
