# Copy-ready final Kaggle post: DueCare closeout and node-first future

This is the final project-update post to publish in the Kaggle community as
Gemma 4 Good judging concludes. The text below is intentionally self-contained,
dated, and candid about completed work, planned provider evaluation, missing
human evidence, and the post-competition hosting change.

Kaggle's [supported CLI](https://github.com/Kaggle/kaggle-cli/blob/main/docs/README.md)
can browse/read forums and manage datasets, models, competitions, and notebooks;
its documented forum commands do not publish a community discussion. Copy the
title, body, and tags below into Kaggle's discussion editor without changing
the evidence labels.

## Title

**DueCare after Gemma 4 Good: a reusable capability-gap architecture, a node-first future, and an honest final status**

## Post body

Hi Kaggle community,

As Gemma 4 Good judging winds down, I wanted to leave one final DueCare update:
what was built, what changed after submission, what still has not been proven,
and how the project will remain available after its centralized demo hosting is
retired.

DueCare began as a Gemma 4 safety project for migrant-worker protection. The
core problem was that a general model could sound reasonable while missing the
specific indicator, rule, evidence path, or safe next step that a worker,
caseworker, platform reviewer, or regulator actually needed. The project grew
into a modular system around the model: deterministic pattern checks, versioned
retrieval, tools, citations, privacy controls, traces, evaluation, notebooks,
review packets, and public knowledge-sharing boundaries.

The most important architectural lesson now has its own public blueprint:

https://tayloramareltech.github.io/gemma4_comp/architecture/capability_gap_blueprint/

It describes a pattern that can be rebuilt for another industry or another LLM
capability gap. The reusable parts are the separation between seven planes:
claims, evidence, runtime harness, evaluation, human governance, public
network/publication, and agent operations. The trafficking-specific rules are
not assumed to transfer. A new domain still needs its own authoritative
sources, rubric, benign controls, privacy policy, escalation paths, and
qualified reviewers.

### What was added or tightened after submission

- The public project-status page, maintainer handoff, Claude Code handoff,
  transition plan, repository maps, and GitHub Pages documentation now agree on
  one current state.
- A backend-free continuity build exports all 51 public website routes and five
  checksum-bound public snapshots from the real FastAPI templates. Mutable
  APIs, accounts, submissions, automation, and private state fail closed.
- Website layout defects were repaired and the current status page was checked
  in real desktop and emulated-mobile rendering, including the new architecture
  and evaluation cards.
- The provider budget is now enforced before seven registered model transports:
  four primary generation routes, adverse-media verification, model-failure
  candidate generation, and contextual judging. Attempts, token ceilings, and
  reviewed worst-case cash are reserved atomically; retries are new attempts.
- The evaluation runner now supports a publication-grade one-dimension-per-call
  protocol and an economical one-call holistic protocol, real DueCare
  GREP/RAG/tool context, response/context/rubric hashes, resumable results, and
  explicit cross-family versus self-family labels.
<!-- audit-allow:drift reason: maps a legacy compatibility name to canonical server automation -->
- Hermes, server automation (including the legacy OpenClaw-compatible name),
  the Public Information Research Monitor, outreach drafting, and human review
  are documented as different things. Agents may propose and route work; they
  cannot promote their own output into truth or claim that civil-society review
  happened.

### Kimi K3 and contextual judging

I also froze a 500-item directional Kimi K3 study instead of leaving “test a
frontier model” as a vague next step.

The exact topology is:

1. 500 baseline Kimi K3 candidate answers;
2. a local deterministic DueCare grade for every successful answer;
3. 500 Gemini 3.1 Pro cross-family judgments with the same versioned DueCare
   context; and
4. 500 separately labeled Kimi K3 contextual self-judgments.

That is a maximum of 1,500 hosted calls. The frozen worst-case reservation is
7,296,582 estimated input tokens, 1,152,000 maximum output tokens, and
US$34.448916 at the rates checked on 2026-07-28.

This campaign has **not run**. Five earlier bounded Kimi baseline-access
requests and a later two-arm baseline/full-harness smoke reached Ollama but
returned HTTP 402 because the account had no extra-usage balance, and no Gemini
API credential is present. Therefore there are zero Kimi candidate
completions, zero Gemini judgments, zero Kimi self-judgments, and zero new human
ratings. Access failures are not benchmark results. The paired smoke did fix a
real full-harness tool-call adapter bug and left an exact tested resume receipt;
Kimi execution is now a funded-later next step rather than a vague or blocking
closeout item. The run instructions are public here:

https://tayloramareltech.github.io/gemma4_comp/research/model_failure_run_readiness/

Paired smoke receipt:

https://github.com/TaylorAmarelTech/gemma4_comp/blob/master/configs/duecare/benchmarks/kimi_k3_harness_lift_smoke_20260728.json

The provider references used to freeze that plan are the official Kimi K3
cloud catalog, Gemini 3.1 Pro Preview model documentation, and Gemini API
pricing. Pricing and access can change, so a future run must recheck all three
before unlocking its ledger:

- https://ollama.com/library/kimi-k3%3Acloud
- https://ai.google.dev/gemini-api/docs/models/gemini-3.1-pro-preview
- https://ai.google.dev/gemini-api/docs/pricing

Kimi's self-judgment would be a bias diagnostic, not independent validation.
Gemini is the primary cross-family automated judge for this directional pilot.
Neither is a substitute for qualified human review.

### What remains incomplete

The human-validation packet contains 364 review items across 182 strata, but it
still has zero qualified independent ratings. The training-data diversification
workbook defines 75 exact risk, benign-neighbor, and counterfactual slots, but
zero content rows have been admitted because source-rights snapshots and
two-person adjudication are still missing. Those gaps remain visible rather
than being filled with synthetic approvals.

High-value next work, if a future maintainer or partner reopens it, is:

- fund and run the frozen Kimi/Gemini phases under their separate hard budgets;
- test Meta Muse Spark 1.1 as another explicitly versioned comparison lane;
- send the disagreement slice, not every easy row, to qualified reviewers;
- complete multilingual, code-switch, benign-control, corridor-diversity, and
  temporal legal-freshness review; and
- operate real partner nodes with consented governance instead of treating a
  public outreach form as an active civil-society network.

### From a central demo hub to durable pages and deployable nodes

Render remains available during competition grading. After grading is
confirmed complete, the plan is to retire the centralized Fly/Render-style
demo service and preserve the public presentation on GitHub Pages:

- Durable project documentation:
  https://tayloramareltech.github.io/gemma4_comp/
- Backend-free 51-route website continuity copy:
  https://tayloramareltech.github.io/duecare-ai-site/
- Source and deployment definitions:
  https://github.com/TaylorAmarelTech/gemma4_comp

That change means the main public site will no longer function as a centralized
mutable hub. Public submissions, accounts, admin state, automation, and live
hub APIs will be unavailable on the static site. This is intentional, not an
outage disguised as continuity.

The software itself remains deployable. An NGO, regulator, researcher,
platform team, or developer can run a local or organization-owned DueCare node
from the repository's Docker/local deployment paths, keep sensitive material
inside that trust boundary, and exchange only reviewed packs, sanitized fact
objects, aggregate signals, or signed/hash-bound artifacts. A partner that
needs mutable coordination can self-host the FastAPI hub rather than depending
on one demonstration server.

The post-competition model is therefore less centralized and more consistent
with the privacy premise: durable public knowledge and reproducibility on
GitHub/Kaggle, with operational intelligence handled by independently governed
nodes.

### Start here

- DueCare workbench:
  https://www.kaggle.com/code/taylorsamarel/duecare-app
- Focused live demo:
  https://www.kaggle.com/code/taylorsamarel/duecare-live-demo
- Fine-tuning and evaluation proof path:
  https://www.kaggle.com/code/taylorsamarel/duecare-fine-tuning-and-evaluation
- Current project status and handoff:
  https://duecare-ai.com/project-status
- Reusable capability-gap architecture:
  https://tayloramareltech.github.io/gemma4_comp/architecture/capability_gap_blueprint/
- Post-competition hosting and node-continuity runbook:
  https://tayloramareltech.github.io/gemma4_comp/POST_COMPETITION_HOSTING_TRANSITION/
- Source:
  https://github.com/TaylorAmarelTech/gemma4_comp

Thank you to everyone who reviewed, tested, challenged, or learned alongside
the project. If someone picks DueCare up later, the goal is that they inherit
not only code, but the decisions, boundaries, reproducible plans, and honest
unknowns needed to improve it safely.

- Taylor

## Suggested tags

`gemma-4-good` `responsible-ai` `llm-evaluation` `rag` `ai-safety`
`human-trafficking` `privacy` `open-source` `local-ai` `kaggle-notebooks`

## Recommended attachments

Use these existing public, synthetic/reviewer-safe assets in this order:

1. `kaggle/01-duecare-exploration-workbench/tests/test-results/screenshots/desktop-chromium-harness-tiles.png`
   - caption: “DueCare's independently toggleable Persona, GREP, RAG, Tools,
     Online, and Import capabilities in the Kaggle workbench.”
2. `kaggle/01-duecare-exploration-workbench/tests/test-results/screenshots/desktop-chromium-model-picker.png`
   - caption: “The shared workbench model service and six public user lanes.”
3. `packages/duecare-llm-chat/src/duecare/chat/static/synthetic/receipt_PH_HK_001.png`
   - caption: “Synthetic fee-camouflage evidence used to test substance-over-form
     recognition; no real worker data.”

## Publication check

Immediately before pasting:

1. Confirm judging has concluded or change only the opening phrase to “as
   judging continues”; do not imply an official date that Kaggle has not posted.
2. Confirm the three Kaggle notebook URLs and both GitHub Pages URLs return 200.
3. Keep the Kimi/Gemini paragraph at zero results unless the frozen campaign
   has actually executed and its report passed claim/privacy review.
4. Keep Render active until the separately documented transition gate passes.
