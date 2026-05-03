---
hide:
  - navigation
  - toc
---

# Duecare

> **Open-source AI safety harness around Google's Gemma 4 — for
> migrant workers, NGOs, regulators, and researchers fighting
> recruitment fraud and trafficking. MIT licensed. Runs offline.**

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

    Open the live chat playground on Kaggle:

    [duecare-chat-playground-with-grep-rag-tools :octicons-arrow-right-24:](https://www.kaggle.com/code/taylorsamarel/duecare-gemma-chat-playground-grep-rag-tools){ .md-button .md-button--primary }

    Click "Run All". Type:

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

    Run the whole stack on a Mac mini in your office:

    ``` bash
    git clone https://github.com/TaylorAmarelTech/gemma4_comp
    cd gemma4_comp
    make demo
    ```

    Read the [90-minute office deployment guide](scenarios/ngo-office-deployment.md)
    for the full setup.

=== "I'm an enterprise"

    Read the [enterprise pilot plan](scenarios/enterprise_pilot.md)
    (30-day adoption, 1.5 FTE, $300-1500/mo) or jump to the
    [chief-architect view](scenarios/chief-architect.md) for the
    integration patterns.

## What ships in the box

<div class="grid cards" markdown>

- :material-shield-check: **Harness**

    42 GREP rules + 26 RAG documents + 11 ILO C029 indicators +
    20 migration corridors. Quantified +56.5pp lift across 207
    hand-graded prompts.

- :material-cellphone-android: **Android app**

    `duecare-journey-android` v0.9. On-device Gemma 4. Encrypted
    SQLCipher journal. Reports tab with NGO intake document.

- :material-server: **Server**

    FastAPI + 17 PyPI packages. Per-tenant token + cost meter.
    Per-tenant rate limits. Prometheus / OpenTelemetry / Loki
    observability stack.

- :material-package-variant-closed: **Containers**

    Multi-arch Docker image at `ghcr.io/tayloramareltech/duecare-llm`.
    Helm chart with HPA + PDB + NetworkPolicy. 13-platform
    cloud deploy cookbook.

- :material-book-open-page-variant: **14 persona walkthroughs**

    From migrant workers to Big Tech CTOs. Day-1 setup + day-2
    operational rhythm + day-30 expansion + when-something-breaks
    table per persona.

- :material-school: **Educator + journalist materials**

    Drop-in lesson plans (1-hour to 2-week). Press kit with
    one-pager + suggested story angles + facts + quotes.

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
- :material-notebook-edit-outline: [**Author's notes**](authors_notes.md) — informal observations, what didn't work, design judgments
- :material-bookshelf: [**Appendices**](appendices/README.md) — index of deeper enclosures linked from the writeup
- :material-format-quote-open: [Press kit](press_kit.md) — one-pager + facts + quotes for journalists
- :material-school: [Educator resources](educator_resources.md) — drop-in lesson plans
- :material-compare: [Comparison vs alternatives](comparison_to_alternatives.md) — when Duecare fits vs Hive / Sift / Azure / OpenAI
- :material-check-decagram: [For judges](FOR_JUDGES.md) — the hackathon-judge view
- :material-view-dashboard: [Readiness dashboard](readiness_dashboard.md) — single-screen status across every dimension
- :material-account-multiple-check: [Persona readiness audit](persona_readiness_audit.md) — happy path verified per persona
- :material-frequently-asked-questions: [FAQ](FAQ.md) — common questions answered

## Headline numbers

The harness, when on, beats the harness off by:

- **+56.5 pp** mean lift across 207 hand-graded prompts
- **+87.5 pp** on jurisdiction-specific rule citations
- **+51.2 pp** on ILO / international convention citations
- **100%** of prompts saw the harness help; 0 saw it hurt

Numbers are reproducible — see the [harness lift report](harness_lift_report.md)
+ [`RESULTS.md`](https://github.com/TaylorAmarelTech/gemma4_comp/blob/master/RESULTS.md)
for the `(git_sha, dataset_version, model_revision)` provenance.

## Privacy is non-negotiable

- **By default, nothing leaves your machine** beyond the one-time AI model download.
- **No telemetry.** No analytics. No phone-home. The maintainer doesn't operate any service your data passes through.
- **Audit log records hashes**, not plaintext.
- **Panic-wipe primitive** in the Android app erases everything in one tap.
- **Open source**, MIT licensed, fork-able.

Read the [threat model](considerations/THREAT_MODEL.md) for the
detailed STRIDE breakdown across 4 trust boundaries.

---

*Built for the [Google Gemma 4 Good Hackathon](https://www.kaggle.com/competitions/gemma-4-good-hackathon)
(Safety & Trust track), submission due 2026-05-18.*
