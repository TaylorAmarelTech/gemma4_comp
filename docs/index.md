---
hide:
  - navigation
  - toc
---

# DueCare: A Gemma 4 Safety Ecosystem

> **Current competition scope (2026-05-25):** the active Kaggle
> judging path is `kaggle/01-duecare-exploration-workbench` plus
> `kaggle/02-live-demo`. Optional proof surfaces live in
> `kaggle/03-universal-llm-benchmark` and
> `kaggle/04-kaggle-community-benchmark`. Appendix notebooks and
> A-series experiments are archived provenance; they are not the
> main run path. See
> [`kaggle/_INDEX.md`](https://github.com/TaylorAmarelTech/gemma4_comp/blob/master/kaggle/_INDEX.md).

> **Open-source AI safety harness around Google's Gemma 4 — for
> migrant workers, NGOs, regulators, and researchers fighting
> recruitment fraud and trafficking. MIT licensed. Runs offline.**

## The ecosystem idea

DueCare is not a single chatbot. It is a Gemma 4 workbench plus a
set of reusable safety components: local model runtime, deterministic
rules, retrieval packs, templates, search, anonymization, evidence
graphs, evaluation, and optional community benchmarks.

The strongest use case is a network of trusted local nodes. A worker,
NGO office, regulator, platform team, or researcher can process raw
case material locally. DueCare helps turn that material into reviewed
fact objects, evidence edges, and risk-pattern summaries. Raw worker
files stay where they belong. Only explicitly reviewed, redacted, and
anonymized facts or aggregate signals move outward.

When many local nodes share those safe fact objects, the ecosystem can
see recruitment-abuse and trafficking patterns that no single office
can see alone: repeated fee requests, passport-retention clauses,
corridor-specific false promises, and cross-case signals that justify
stronger prevention, investigation, and worker support.

## What it does

A 23-year-old domestic worker leaves the Philippines for Hong Kong.
A recruiter charges her ₱50,000 in "training fees" before her visa
is released — but Philippine law says that fee is illegal.

She doesn't know that. She pays.

Duecare is the tool she — or her caseworker, or her lawyer, or her
country's labor regulator — can use to spot that the fee is illegal,
in 5 seconds, with the actual statute citation, before any harm
happens. Or after, to recover the money.

## Try it now (2 minutes)

=== "I'm curious"

    Open the active DueCare App on Kaggle:

    [duecare-app :octicons-arrow-right-24:](https://www.kaggle.com/code/taylorsamarel/duecare-app){ .md-button .md-button--primary }

    Click "Run All". When the Cloudflare URL appears, open the
    workbench and try Bulk File Review, Knowledge Extraction, Search,
    Templates, or Anonymization & Sharing.

    For the quick chat path, type:

    > *Is a 50,000 PHP training fee legal for a Filipino domestic
    > worker going to Hong Kong?*

    The harness cites POEA Memorandum Circular 14-2017 §3.

=== "I'm a migrant worker"

    On your Android phone:

    [Get the v0.9 APK :octicons-arrow-right-24:](https://github.com/TaylorAmarelTech/duecare-journey-android/releases){ .md-button .md-button--primary }

    Read the [worker self-help guide](scenarios/worker-self-help.md)
    (also available in [Tagalog draft](scenarios/translations/worker-self-help.tl.md)
    and [Spanish draft](scenarios/translations/worker-self-help.es.md)).

=== "I'm an NGO director"

    Start with the active Kaggle demo or a local office deployment:

    ``` bash
    git clone https://github.com/TaylorAmarelTech/gemma4_comp
    cd gemma4_comp
    make demo
    ```

    Read the [90-minute office deployment guide](scenarios/ngo-office-deployment.md)
    for the full setup.

=== "I'm a developer or integrator"

    Install the Python packages, run the public-surface checks, and
    choose the lane that matches your deployment:

    ``` bash
    python -m pip install -e packages/duecare-llm-chat
    python scripts/validate_public_surface.py
    ```

    Read the [install guide](install.md), [embedding guide](embedding_guide.md),
    or [chief-architect view](scenarios/chief-architect.md).

## Portable onboarding paths

| Path | Start | What Leaves The Local Node |
|---|---|---|
| **Kaggle judge** | Run Kernel 01, then open Getting Started, Bulk File Review, and the Ecosystem Map. | Replay JSON, graph export, comparison scores, UI audit. |
| **NGO & regulator** | Process a local case bundle, review evidence, draft templates, and anonymize. | Reviewed graph, referral draft, `knowledge_files.zip`, `redacted_submission.json`. |
| **Individual worker / mobile** | Ask local questions, save private notes, and prepare intake material. | Worker-approved note or intake draft. |
| **Researcher** | Import reviewed packs and run public-source search through Search Safety. | Aggregate signal table, public-source proposal, benchmark row. |
| **Developer / integration partner** | Install `duecare-llm-chat` and inspect `/api/portability`. | Route inventory, type catalog, sample manifest, reusable harness contract. |
| **Benchmark user** | Use optional Kernel 03 or 04 after the active demo path is stable. | Synthetic or anonymized prompt rows, judge rubric, comparison table, reproducibility metadata. |

## What ships in the box

<div class="grid cards" markdown>

- :material-shield-check: **Harness**

    100+ GREP rules + 50+ RAG documents + ILO indicator and corridor
    packs. Quantified lift is documented in the reproducibility reports.

- :material-cellphone-android: **Android app**

    `duecare-journey-android` v0.9. On-device Gemma 4. Encrypted
    SQLCipher journal. Reports tab with NGO intake document.

- :material-server: **Server**

    FastAPI + the Duecare package family. Per-tenant token + cost meter.
    Per-tenant rate limits. Prometheus / OpenTelemetry / Loki
    observability stack.

- :material-package-variant-closed: **Containers**

    Multi-arch Docker image at `ghcr.io/tayloramareltech/duecare-llm`.
    Helm chart with HPA + PDB + NetworkPolicy. Multi-platform
    cloud deploy cookbook.

- :material-book-open-page-variant: **Persona walkthroughs**

    From migrant workers to Big Tech CTOs. Day-1 setup + day-2
    operational rhythm + day-30 expansion + when-something-breaks
    table per persona.

- :material-school: **Educator + journalist materials**

    Drop-in lesson plans (1-hour to 2-week). Press kit with
    one-pager + suggested story angles + facts + quotes.

- :material-share-variant: **Anonymized fact-object sharing**

    Local deployments can create reviewed, redacted fact objects and
    graph evidence without uploading raw worker files. Shared safely,
    those objects become corridor intelligence, knowledge-pack updates,
    and benchmark rows.

</div>

## Pick your path

Sorted by who you are:

| You are... | Read |
|---|---|
| **OFW / migrant worker** | [Worker self-help](scenarios/worker-self-help.md) |
| **Caseworker** | [Caseworker workflow](scenarios/caseworker_workflow.md) |
| **NGO director** | [NGO office deployment](scenarios/ngo-office-deployment.md) |
| **Legal aid lawyer** | [Lawyer evidence prep](scenarios/lawyer-evidence-prep.md) |
| **Government regulator** | [Regulator pattern analysis](scenarios/regulator-pattern-analysis.md) |
| **Embassy / consulate officer** | [Embassy + consular workflow](scenarios/embassy-consular.md) |
| **ILO / IOM regional staff** | [Supra-national analysis](scenarios/ilo-iom-regional.md) |
| **Recruitment compliance officer** | [Self-audit](scenarios/recruiter-self-audit.md) |
| **Researcher** | [Researcher analysis](scenarios/researcher-analysis.md) |
| **Investigative journalist** | [Journalist investigation](scenarios/journalist-investigation.md) |
| **IT director** | [IT director TCO + ops](scenarios/it-director.md) |
| **Chief architect** | [Architect integration](scenarios/chief-architect.md) |
| **VP Engineering** | [VP 90-day plan](scenarios/vp-engineering.md) |
| **Platform CTO at Big Tech** | [Enterprise pilot](scenarios/enterprise_pilot.md) |

## Quick links

- :material-map-marker-radius: [**System map**](system_map.md) — interactive bird's-eye view of all components, users, deployments, notebooks
- :material-sitemap-outline: [**System components and critical paths**](system_components_and_critical_paths.md) — stable component map, harness inventory, critical paths, users, and drift rules
- :material-notebook-edit-outline: [**Author's notes**](authors_notes.md) — informal observations, what didn't work, design judgments
- :material-bookshelf: [**Appendices**](appendices/README.md) — index of deeper enclosures linked from the writeup
- :material-format-quote-open: [Press kit](press_kit.md) — one-pager + facts + quotes for journalists
- :material-school: [Educator resources](educator_resources.md) — drop-in lesson plans
- :material-compare: [Comparison vs alternatives](comparison_to_alternatives.md) — when Duecare fits vs Hive / Sift / Azure / OpenAI
- :material-check-decagram: [For judges](FOR_PEER_REVIEW.md) — the hackathon-judge view
- :material-view-dashboard: [Readiness dashboard](readiness_dashboard.md) — single-screen status across every dimension
- :material-account-multiple-check: [Persona readiness audit](persona_readiness_audit.md) — happy path verified per persona
- :material-frequently-asked-questions: [FAQ](FAQ.md) — common questions answered

### Verifiability + reproducibility (judge-focused)

- :material-clipboard-check: [**Reproducibility**](reproducibility.md) — every quantitative claim grounded with `(git_sha, dataset_version, eval_set, grader_version)` provenance + one-command re-measurement path
- :material-table-of-contents: [**Corpus index**](corpus_index.md) — source-of-truth pointers for the live GREP, RAG, tool, rubric, and judge inventories
- :material-compare-horizontal: [**Stock vs harnessed examples**](stock_vs_harnessed.md) — 5 textbook prompts side-by-side (mean lift 4.6% → 88.4%)
- :material-tune-vertical: [**Archived A-00 proof path**](FOR_PEER_REVIEW.md#archived-a-00-proof-path) — preconfigured baseline, harness, optional LoRA, judging, and export run
- :material-clock-fast: [**Judge 5-min test plan**](peer_review_5min_test_plan.md) — the entry point for hackathon judges

## Headline proxy evidence

The measured harness-lift report shows current smoke / regression
evidence. These are not field-deployment, production-traffic, or
weeks-long local Gemma reliability numbers:

- **+51.4 pp** mean lift across the published 200+ prompt proxy set
- **+73.8 pp** on jurisdiction-specific rule citations
- **+55.4 pp** on ILO / international convention citations
- **+21.2 pp** on substance-over-form analysis
- **Nearly all** checked proxy prompts saw the harness help; the
  generated report lists the exact current count

Numbers are reproducible — see the [harness lift report](harness_lift_report.md),
the [reproducibility doc](reproducibility.md) (provenance for every
quantitative claim), and [`RESULTS.md`](https://github.com/TaylorAmarelTech/gemma4_comp/blob/master/RESULTS.md)
for the `(git_sha, dataset_version, model_revision)` tuples.

**Measurement note:** these numbers were regenerated from the current
source on May 25, 2026 with `python scripts/rubric_comparison.py`.
Re-run that command before copying the figures into a new public claim.
Run and archive live Gemma outputs before claiming long-run citation
traceability or field performance.

## Sensitive data stays local

- **By default, nothing leaves your machine** beyond the one-time AI model download.
- **No telemetry.** No analytics. No phone-home. The maintainer doesn't operate any service your data passes through.
- **Audit log records hashes**, not plaintext.
- **Panic-wipe primitive** in the Android app erases everything in one tap.
- **Open source**, MIT licensed, fork-able.

Read the [threat model](considerations/THREAT_MODEL.md) for the
detailed STRIDE breakdown across 4 trust boundaries.

---

*Built for the [Google Gemma 4 Good Hackathon](https://www.kaggle.com/competitions/gemma-4-good-hackathon)
(Safety & Trust track), submitted 2026-05-18.*
