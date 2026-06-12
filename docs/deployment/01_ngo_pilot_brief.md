# Path 1 — Single NGO pilot brief

For an NGO of 5 to 50 caseworkers serving migrant workers,
trafficking survivors, or domestic-worker rights cases. Examples in
this audience: Damayan (NYC), Kalayaan (UK), Mission for Migrant
Workers (HK), Bhumika Foundation (NP), POHDH (Haiti), Polaris
(US), HOME (Singapore), ATLEU (UK), ECPAT national chapters.

## What you get

A local AI workbench that helps your caseworkers:

- Triage incoming case messages for trafficking indicators
- Extract structured case facts from chat screenshots, scanned
  contracts, and recruitment ads
- Draft jurisdiction-specific complaints (POEA, BP2MI, BMET, DOL,
  GLAA, etc.) with statute citations already filled in
- Look up corridor fee caps, statute references, and peer NGO
  contacts without leaving the workbench
- Anonymise sensitive case data before any external sharing

It runs on a single laptop. No cloud account, no API keys, no
egress to a third-party model. The 451 GREP rules and 859 RAG
documents are bundled with the install.

## What you provide

| Resource | Minimum | Recommended |
|----------|---------|-------------|
| Laptop | 16 GB RAM, modern CPU | 32 GB RAM, dedicated GPU (RTX 3060 / 4060 / Apple M-series) |
| Storage | 30 GB free | 60 GB free |
| Network | Internet for the initial install only | Same; no egress required after install |
| Operator time | 1 caseworker + 1 IT helper, 1 day | Same + 1 hour/week ongoing |
| Domain knowledge | Existing caseload context | Specific corridor focus declared up-front |

## What is in scope

- **Chat triage** — paste or upload a worker's WhatsApp / Messenger
  history, get an ILO-indicator summary, suspected fee-camouflage
  labels, suggested referrals
- **Document review** — upload a recruitment contract or scanned
  job ad, get red-flag analysis with statute citations
- **Complaint drafting** — pick a template (34 available, including
  POEA, DMW, BP2MI, BMET, DoFE, DOLAB, MoM, GLAA, FWO, DOL WHD,
  HK Labour Department, Saudi MHRSD, UAE MoHRE, Qatar MoL,
  Polaris hotline referral, IOM referral, UK NRM referral) and let
  Gemma 4 fill in case-specific blanks while preserving the
  pre-baked legal citations
- **Knowledge lookup** — corridor fee cap for the worker's route,
  appropriate NGO contact bundle, applicable ILO conventions
- **Anonymisation** — produces a redacted envelope a caseworker can
  share with a peer NGO, regulator, or shared knowledge hub

## What is out of scope (initial pilot)

- Direct integration with existing case-management software — that
  is a phase 2 conversation (export/import via JSONL works on day
  one)
- Multi-user concurrent access — the workbench is single-operator
  by design; if you need multi-user, that is path 3 (API mode)
- Mobile delivery to workers — the LiteRT-based mobile path is
  separate; pilot the desktop workbench first

## Install steps (for the IT helper)

```bash
# Verify Python 3.11+
python --version

# Create a clean environment (Windows PowerShell shown; bash similar)
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip

# Install DueCare (one command pulls all 17 packages via the meta)
pip install duecare-llm

# Pull Gemma 4 weights (one-time, ~6 GB for E4B)
duecare model pull gemma-4-e4b

# Launch the workbench
duecare workbench
```

The workbench opens at `http://localhost:8080`. The first cell of
the activity log shows model load progress (30 seconds for E2B, 60
to 90 seconds for E4B on CPU; faster with GPU).

## First-week checklist for the operator

| Day | Activity | Success signal |
|-----|----------|----------------|
| 1 | Install, model load, run sample case bundle | Sample case produces a populated report with citations |
| 2 | Run three of your own real cases through chat triage | At least two produce useful flags or referrals |
| 3 | Try the process harness on a scanned contract | Extraction populates the case-fact card |
| 4 | Draft one complaint using a template | Statute citations land verbatim; only case-specific blanks need manual edit |
| 5 | Try the anonymisation gate before sharing a case to a peer | Anonymizer redacts PII; envelope is shareable |
| 6 | Pick the two personas you use most (worker_first_person, lawyer_research, ngo_intake, caseworker_active, etc.) and set as defaults | Workbench remembers your defaults |
| 7 | Review what the workbench got wrong this week | List of issues for the corridor tuning conversation |

## 30-day success metrics

Pick the ones that matter most for your operation:

- **Triage time per case** — target: 50% reduction vs. current
  process
- **First-draft complaint time** — target: 30 minutes (down from
  several hours)
- **Citation accuracy** — target: zero hallucinated statutes after
  the corridor-tuning pass
- **Caseworker confidence** — target: 80% of caseworkers report the
  workbench was "useful" or "very useful" on weekly survey
- **Anonymisation correctness** — target: zero PII leaks in 100
  randomly-audited envelopes

## Trust boundary (plain English)

1. Worker case files, chat screenshots, scanned documents, IDs,
   addresses, phone numbers, and case identifiers stay on the
   caseworker's laptop. They do not leave the device.
2. The Gemma 4 model is loaded from local disk and runs in-process.
   It does not call out to any external API.
3. The GREP / RAG / templates / personas / corridor caps / NGO
   contacts knowledge layer is bundled with the install. It is
   versioned at a known commit SHA, verifiable via
   `python scripts/verify_knowledge_surfaces.py`.
4. The only data that ever leaves the laptop is content the
   caseworker explicitly chooses to share. That content first passes
   through the anonymisation gate, which redacts PII to tagged
   placeholders. The original PII is hashed (SHA-256) for audit
   purposes; the plaintext is never persisted to the share envelope.
5. The shared envelope is portable — JSON, no proprietary format.
   You can pass it to a peer NGO via email attachment, or upload it
   to the shared knowledge hub if you join path 2.

## Where this fits in the broader DueCare project

This is the smallest deployable unit of the DueCare system. It is
the same software the larger paths use, configured for a single
operator. If your NGO grows into a regional coordinator, path 2 is
the natural next step. If you become a regulator partner, path 3.
If you license the model to a platform, path 4.

## Next concrete action

If you are evaluating DueCare for your NGO:

1. Read [`01_ngo_caseworker_quickstart.md`](01_ngo_caseworker_quickstart.md)
   — the day-to-day workflow your caseworkers will follow.
2. Pick a single corridor or sector to pilot first (PH→HK domestic
   worker, NP→Gulf construction, etc.). Tell us which one — that
   determines which corridor caps + templates we pre-load for you.
3. Schedule a 30-minute install session. We will sit with your IT
   helper to get the workbench live and walk one of your real cases
   through it.

Contact: `amarel.taylor.s@gmail.com` (DueCare project lead,
Gemma 4 Good Hackathon submission 2026-05-18).
